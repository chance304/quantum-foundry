"""Pipeline: wires materials -> dft -> transport -> thermal -> manufacturability
into one PipelineResult. Never imports a concrete backend class directly —
only each layer's get_backend() factory, so swapping stub -> real is a
one-line RunConfig change (see docs/ARCHITECTURE.md's "stub/real seam").

M9a (2026-07-27, docs/M9_PLAN.md): when config.device_geometry.stacked_tiers
is set, run() takes a separate path (_run_stacked) that runs dft+transport
once per DeviceTier instead of once for the whole device -- a CFET's n-tier
and p-tier are genuinely different materials/carriers, not one calculation
run twice. The single-tier path (_run_single) is completely unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from .. import dft, manufacturability, thermal, transport
from ..dft.results import DFTResult
from ..manufacturability.results import YieldResult
from ..materials.registry import MaterialsDB
from ..materials.schema import MaterialRecord
from ..thermal.beol_budget import check_beol_budget, check_m3d_layer_transfer_budget
from ..thermal.hotspot_backend import default_stacked_stack_from_geometry
from ..thermal.hotspot_backend import run_stacked as hotspot_run_stacked
from ..thermal.results import ThermalResult
from ..thermal.stub import default_stack_from_geometry
from ..transport.results import DeviceTier, TransportResult
from .config import RunConfig


@dataclass
class StackedTierResult:
    """One stacked tier's real, independent dft+transport result -- only
    populated when DeviceGeometry.stacked_tiers is set (M9a). Lives in
    PipelineResult.extra['stacked_tier_results'], not a new top-level field,
    since PipelineResult.material/dft_result/transport_result stay singular
    (see Pipeline._run_stacked()'s docstring for what they mean in this case).
    """
    tier: DeviceTier
    material: MaterialRecord
    dft_result: DFTResult
    transport_result: TransportResult


@dataclass
class PipelineResult:
    material: MaterialRecord
    dft_result: DFTResult
    transport_result: TransportResult
    thermal_result: ThermalResult
    yield_result: YieldResult
    run_config: RunConfig
    generated_at: datetime
    # Added 2026-07-22: every other Result type already has one. Populated
    # with the BEOL/M3D thermal-budget hard-stop checks below (previously
    # nowhere enforced -- a real gap the standards audit flagged).
    extra: dict[str, Any] = field(default_factory=dict)


def _tier_geometry(base_geometry, tier: DeviceTier):
    # Real, stated assumption: every stacked tier shares the base geometry's
    # channel_length_nm/channel_width_nm/gate stack -- true by construction
    # for a real CFET (same footprint, stacked tiers is the whole point).
    # stacked_tiers=None on the per-tier geometry: each tier's own transport
    # run models a single planar channel, not a recursively "stacked" one.
    return replace(
        base_geometry,
        channel_material_id=tier.channel_material_id,
        channel_thickness_nm=tier.channel_thickness_nm,
        stacked_tiers=None,
    )


class Pipeline:
    def __init__(self, materials_db: MaterialsDB | None = None):
        self._db = materials_db or MaterialsDB()

    def run(self, config: RunConfig) -> PipelineResult:
        if config.device_geometry.stacked_tiers:
            return self._run_stacked(config)
        return self._run_single(config)

    def _run_single(self, config: RunConfig) -> PipelineResult:
        material = self._db.get(config.material_id)

        dft_result = dft.get_backend(config.dft.backend).run(material, config.dft.params)
        transport_result = transport.get_backend(config.transport.backend).run(
            material, dft_result, config.device_geometry, config.transport.params
        )

        stack = config.material_stack or default_stack_from_geometry(config.device_geometry)
        thermal_result = thermal.get_backend(config.thermal.backend).run(
            transport_result, stack, config.thermal.params
        )

        yield_result = manufacturability.get_backend(config.manufacturability.backend).run(
            transport_result, config.manufacturability.params
        )

        return PipelineResult(
            material=material,
            dft_result=dft_result,
            transport_result=transport_result,
            thermal_result=thermal_result,
            yield_result=yield_result,
            run_config=config,
            generated_at=datetime.now(UTC),
            extra={
                "beol_budget_check": check_beol_budget(thermal_result.max_junction_temp_C),
                "m3d_layer_transfer_check": check_m3d_layer_transfer_budget(thermal_result.max_junction_temp_C),
            },
        )

    def _run_tiers(self, config: RunConfig) -> list[StackedTierResult]:
        """M9a's real per-tier work -- no thermal/HotSpot dependency, so
        this is directly unit-testable without the real HotSpot binary
        (mirrors thermal/hotspot_backend.py's own split between pure-Python
        layer-file writing and the binary-invoking run()/run_stacked()).
        """
        tiers = config.device_geometry.stacked_tiers
        assert tiers  # guaranteed by the run() dispatch's stacked_tiers check
        tier_results: list[StackedTierResult] = []
        for tier in tiers:
            tier_material = self._db.get(tier.channel_material_id)
            tier_dft_params = {**config.dft.params, "carrier_type": tier.carrier_type}
            tier_dft_result = dft.get_backend(config.dft.backend).run(tier_material, tier_dft_params)
            tier_geometry = _tier_geometry(config.device_geometry, tier)
            tier_transport_params = {**config.transport.params, "carrier_type": tier.carrier_type}
            tier_transport_result = transport.get_backend(config.transport.backend).run(
                tier_material, tier_dft_result, tier_geometry, tier_transport_params
            )
            tier_results.append(StackedTierResult(tier, tier_material, tier_dft_result, tier_transport_result))
        return tier_results

    def _run_stacked(self, config: RunConfig) -> PipelineResult:
        """M9a: one dft+transport run per DeviceTier. Thermal currently
        requires backend='hotspot' -- the stub thermal backend has no
        multi-tier model yet (M9b only extended hotspot_backend.py, see
        docs/M9_PLAN.md). Manufacturability/yield is evaluated against tier
        0's transport result only (same "primary tier" choice as
        material/dft_result/transport_result below) -- a real, named
        simplification, not a fabricated combined-tier yield model.
        """
        tier_results = self._run_tiers(config)

        if config.thermal.backend != "hotspot":
            raise ValueError(
                "Stacked-tier runs (DeviceGeometry.stacked_tiers) currently require "
                "thermal.backend='hotspot' -- the stub thermal backend has no "
                "multi-tier model yet (see docs/M9_PLAN.md, M9b)."
            )
        stack = config.material_stack or default_stacked_stack_from_geometry(config.device_geometry)
        thermal_result = hotspot_run_stacked(
            [r.transport_result for r in tier_results], stack, config.thermal.params
        )

        primary = tier_results[0]
        yield_result = manufacturability.get_backend(config.manufacturability.backend).run(
            primary.transport_result, config.manufacturability.params
        )

        return PipelineResult(
            material=primary.material,
            dft_result=primary.dft_result,
            transport_result=primary.transport_result,
            thermal_result=thermal_result,
            yield_result=yield_result,
            run_config=config,
            generated_at=datetime.now(UTC),
            extra={
                "beol_budget_check": check_beol_budget(thermal_result.max_junction_temp_C),
                "m3d_layer_transfer_check": check_m3d_layer_transfer_budget(thermal_result.max_junction_temp_C),
                "stacked_tier_results": tier_results,
                "stacked_primary_tier_note": (
                    "material/dft_result/transport_result/yield_result above are tier "
                    "0's real values, not a fabricated combination across tiers -- see "
                    "extra['stacked_tier_results'] for every tier's own real result."
                ),
            },
        )
