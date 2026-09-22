"""M6 — n/p channel-material search targeting the 2D-CMOS n/p-asymmetry
gap (MoS2 = best real n-type 2D channel, WSe2/WS2 = best real p-type
channels, no single material does both well).

Scope honesty: this is an n/p *channel-material* search — each candidate is
evaluated as a uniform-channel FET in each role — not a literal bonded-
heterostructure simulation. No band-alignment/interlayer-coupling physics
exists anywhere in this pipeline yet (a real, current gap). The module is
named heterostructure.py to match the already-established M6 milestone name
(the n/p-asymmetry framing from the 2D-CMOS literature), not because it
models an actual
stacked heterostructure.

Deliberately no a priori n-only/p-only assignment: every candidate is run
in *both* roles (carrier_type="electron" and "hole"), testing the
MoS2-n/WSe2-WS2-p hypothesis via simulation rather than assuming it.

Reuses pareto.pareto_front() unmodified, per its original design intent.
Does not reuse sweep() -- that varies one param on one fixed material; this
varies material_id itself, which needs its own per-candidate RunConfig.

Known real limitation (found while building this search, not fixed here):
max_junction_temp_C objective values come from thermal/stub.py's lumped-RC
model, which has no lateral heat-spreading term. At this search's nm-scale
device area against a bulk substrate thickness, that produces physically
absurd absolute Tj values (hundreds of thousands of degrees) -- the same
scale-mismatch class already found and fixed for the real HotSpot backend
via thermal/hotspot_backend.py's _pad_to_die_footprint(), left unaddressed
in the stub. Tj is still used here as a real, ordinal (relative) signal
between candidates -- it should not be read as a physically meaningful
absolute temperature until the stub gets an equivalent fix (see docs/ROADMAP.md).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ..materials.registry import MaterialsDB
from ..transport.results import DeviceGeometry
from .config import RunConfig, StageConfig
from .pareto import pareto_front
from .pipeline import Pipeline, PipelineResult

# The 7 real 2D channel materials from docs/ROADMAP.md's materials-scale-up
# table. Excludes HfO2/ZrO2 -- those are gate dielectrics, not channel
# candidates.
_CHANNEL_CANDIDATE_MATERIAL_IDS: tuple[str, ...] = (
    "MoS2_monolayer",
    "WSe2_monolayer",
    "WS2_monolayer",
    "MoTe2_monolayer",
    "WTe2_monolayer",
    "black_phosphorus_monolayer",
    "graphene_monolayer",
)

_OBJECTIVES = {
    "ion_uA_per_um": lambda r: r.transport_result.ion_uA_per_um,
    "subthreshold_swing_mV_dec": lambda r: r.transport_result.subthreshold_swing_mV_dec,
    "max_junction_temp_C": lambda r: r.thermal_result.max_junction_temp_C,
    "yield_fraction": lambda r: r.yield_result.yield_fraction,
}
_MINIMIZE = {"subthreshold_swing_mV_dec", "max_junction_temp_C"}


@dataclass
class CandidateResult:
    material_id: str
    carrier_type: str  # "electron" | "hole"
    pipeline_result: PipelineResult | None
    excluded_reason: str | None  # set iff pipeline_result is None


@dataclass
class HeterostructureSearchResult:
    n_candidates: list[CandidateResult]
    p_candidates: list[CandidateResult]
    n_pareto_front: list[PipelineResult]
    p_pareto_front: list[PipelineResult]
    # None whenever the front has != 1 member -- a real trade-off/tie
    # between multiple candidates, not something to fabricate a winner for.
    recommended_n_material_id: str | None
    recommended_p_material_id: str | None
    generated_at: datetime


def _geometry_for(material_id: str) -> DeviceGeometry:
    # Mirrors qf run's own CLI defaults for consistency. "Si" isn't seeded
    # in MaterialsDB, so the thermal stub's existing, already-flagged
    # fallback_conductivity_used_for path applies here too -- same as qf
    # run today, not a new gap introduced by this module.
    return DeviceGeometry(
        channel_length_nm=20.0,
        channel_width_nm=100.0,
        channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0,
        gate_oxide_material_id="HfO2",
        channel_material_id=material_id,
        substrate_material_id="Si",
    )


def _run_candidate(pipeline: Pipeline, material_id: str, carrier_type: str) -> CandidateResult:
    config = RunConfig(
        material_id=material_id,
        device_geometry=_geometry_for(material_id),
        # dft must get carrier_type too (added 2026-07-22) -- otherwise its
        # gate still conservatively requires both effective masses even when
        # only one role is actually being searched, blocking materials like
        # WSe2 that have just one real, trustworthy mass. See dft/stub.py.
        dft=StageConfig(backend="stub", params={"carrier_type": carrier_type}),
        transport=StageConfig(backend="stub", params={"carrier_type": carrier_type}),
    )
    try:
        result = pipeline.run(config)
    except ValueError as exc:
        # Catches the real refusal from either dft/stub.py's required-fields
        # gate or transport/stub.py's missing-effective-mass gate -- not
        # pre-duplicating either's field-requirement list here.
        return CandidateResult(material_id, carrier_type, None, str(exc))
    return CandidateResult(material_id, carrier_type, result, None)


def _front(candidates: list[CandidateResult]) -> list[PipelineResult]:
    successes = [c.pipeline_result for c in candidates if c.pipeline_result is not None]
    return pareto_front(successes, _OBJECTIVES, _MINIMIZE)


def search(
    materials_db: MaterialsDB | None = None,
    candidate_material_ids: tuple[str, ...] = _CHANNEL_CANDIDATE_MATERIAL_IDS,
) -> HeterostructureSearchResult:
    pipeline = Pipeline(materials_db)
    n_candidates = [_run_candidate(pipeline, mid, "electron") for mid in candidate_material_ids]
    p_candidates = [_run_candidate(pipeline, mid, "hole") for mid in candidate_material_ids]

    n_front = _front(n_candidates)
    p_front = _front(p_candidates)

    return HeterostructureSearchResult(
        n_candidates=n_candidates,
        p_candidates=p_candidates,
        n_pareto_front=n_front,
        p_pareto_front=p_front,
        recommended_n_material_id=n_front[0].material.material_id if len(n_front) == 1 else None,
        recommended_p_material_id=p_front[0].material.material_id if len(p_front) == 1 else None,
        generated_at=datetime.now(UTC),
    )
