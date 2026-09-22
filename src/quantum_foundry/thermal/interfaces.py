"""Contract for the thermal/mechanical stage.

Registered in `thermal/__init__.py`'s `get_backend(name, **params)`. See
`docs/ARCHITECTURE.md`'s "The stub/real seam" for the cross-stage pattern.

Today's registered backends: `"stub"` (`thermal/stub.py` — lumped-RC
approximation), `"hotspot"` (`thermal/hotspot_backend.py` — real compact
thermal model via the vendored HotSpot binary; also supports a
`run_stacked()` multi-tier path with synthetic Kapitza interface layers).
Deferred: FEniCSx (primary 3D FEA) and Elmer (coupled thermo-mechanical),
see `docs/M5_PLAN.md` — not yet registered here. `thermal/
mesh_generation.py` (gmsh-based layered-slab meshing) is real, tested
groundwork for that FEA path but is not itself a `ThermalBackend`.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..transport.results import TransportResult
from .results import MaterialStack, ThermalResult


@runtime_checkable
class ThermalBackend(Protocol):
    """A single thermal/mechanical backend (junction temp, thermal resistance).

    Attributes:
        name: Registry key this backend was constructed under.
        is_stub: Whether `run()` is a real solve (`False`) or an
            approximation (`True`); propagated into `ThermalResult
            .provenance.is_stub`.
    """

    name: str
    is_stub: bool

    def run(
        self, transport_result: TransportResult, stack: MaterialStack, params: dict
    ) -> ThermalResult:
        """Compute (or approximate) this device's thermal behavior.

        Args:
            transport_result: The upstream `TransportResult` — its
                `power_density_W_per_um2` is the real heat source driving
                this stage.
            stack: `MaterialStack` — an ordered list of `ThermalLayer`
                entries (`material_id`, `thickness_nm`, `role` — e.g.
                `"channel" | "gate_oxide" | "substrate" | "contact_metal"`)
                describing the device's vertical cross-section.
            params: Backend-specific run parameters.

        Returns:
            A `ThermalResult` (see `thermal/results.py`):
            `max_junction_temp_C` (deg C), `thermal_resistance_K_per_W`
            (K/W), optional `stress_MPa` (MPa, real FEA backends only —
            not computed by the lumped-RC stub or HotSpot's compact
            model), an optional `FieldHandle` for spatially-resolved output
            (`format` is one of `"xdmf_hdf5" | "lumped_scalar" |
            "hotspot_grid_steady"`), and a `ProvenanceInfo` with `is_stub`
            set to this backend's own value.
        """
        ...
