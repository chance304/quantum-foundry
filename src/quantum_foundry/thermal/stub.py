"""Stub thermal backend: series lumped 1D thermal-resistance network across
the device stack, using each layer's real cited thermal_conductivity_W_mK
from materials/ (falls back to a flagged order-of-magnitude default only
when a layer's material has no data — flagged in `extra`, never silently
treated as equally trustworthy).

Fixed 2026-07-22 (found while building M6): with no lateral heat-spreading
term, using the bare nm-scale device area for every layer -- including a
300um-thick substrate -- produced physically absurd Tj values (hundreds of
thousands of degrees) for realistic device geometries. Same scale-mismatch
class already found and fixed for the real HotSpot backend via
`_pad_to_die_footprint()` (thermal/hotspot_backend.py): a real transistor is
never thermally isolated at its own bare footprint, it sits inside a
realistically-sized die. Fix here floors the *effective area* used for the
resistance calculation at `_MIN_DIE_AREA_UM2` (matching HotSpot's
`_MIN_DIE_SIDE_M`), while power dissipation still uses the real device area.
This remains an approximation -- a single floored area, not a true lateral
spreading gradient -- so it stays an ordinal/relative-comparison signal
between candidates, not a real absolute-temperature simulation (see
`orchestration/heterostructure.py`'s own docstring, which already flags this
result as such).
"""
from __future__ import annotations

from ..materials.registry import MaterialsDB
from ..provenance import ProvenanceInfo
from ..transport.results import TransportResult
from .results import MaterialStack, ThermalLayer, ThermalResult

STUB_TOOL_VERSION = "lumped-rc-stub-0.1"
_FALLBACK_K_W_MK = 1.4  # bulk-SiO2-order-of-magnitude default, NOT a citation
_DEFAULT_SUBSTRATE_THICKNESS_NM = 300_000.0  # 300um default Si wafer
_MIN_DIE_AREA_UM2 = 1e4  # (100um)^2 -- matches hotspot_backend.py's _MIN_DIE_SIDE_M,
# same physical justification: a real device sits inside a realistically-sized
# die, never thermally isolated at its own bare nm-scale footprint.


def run(
    transport_result: TransportResult,
    stack: MaterialStack,
    params: dict,
    materials_db: MaterialsDB | None = None,
) -> ThermalResult:
    db = materials_db or MaterialsDB()
    geom = transport_result.device_geometry
    area_um2 = geom.channel_width_nm * geom.channel_length_nm * 1e-6
    effective_area_um2 = max(area_um2, _MIN_DIE_AREA_UM2)
    padding_applied = effective_area_um2 > area_um2

    total_r = 0.0
    fallback_used: list[str] = []
    for layer in stack.layers:
        k = db.get(layer.material_id).thermal_conductivity_W_mK if layer.material_id in db else None
        if k is None:
            k = _FALLBACK_K_W_MK
            fallback_used.append(layer.material_id)
        total_r += (layer.thickness_nm * 1e-9) / (k * (effective_area_um2 * 1e-12))

    t_ambient = params.get("ambient_temp_C", 25.0)
    power_w = transport_result.power_density_W_per_um2 * area_um2
    t_junction = t_ambient + power_w * total_r

    return ThermalResult(
        max_junction_temp_C=t_junction,
        thermal_resistance_K_per_W=total_r,
        stress_MPa=None,
        field_handle=None,
        provenance=ProvenanceInfo(
            backend_name="thermal_stub_lumped_rc", is_stub=True, tool_version=STUB_TOOL_VERSION
        ),
        extra={
            "layers": [layer.material_id for layer in stack.layers],
            "fallback_conductivity_used_for": fallback_used,
            "synthetic_die_area_padding_applied": padding_applied,
        },
    )


def default_stack_from_geometry(geometry) -> MaterialStack:
    layers = [
        ThermalLayer(geometry.channel_material_id, geometry.channel_thickness_nm, "channel"),
        ThermalLayer(geometry.gate_oxide_material_id, geometry.gate_oxide_thickness_nm, "gate_oxide"),
    ]
    if geometry.substrate_material_id:
        layers.append(
            ThermalLayer(geometry.substrate_material_id, _DEFAULT_SUBSTRATE_THICKNESS_NM, "substrate")
        )
    return MaterialStack(layers=layers)


class LumpedRCThermalStub:
    name = "stub"
    is_stub = True

    def run(self, transport_result, stack, params, materials_db=None):
        return run(transport_result, stack, params, materials_db)
