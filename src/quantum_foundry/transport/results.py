"""Device transport layer result types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..provenance import ProvenanceInfo


@dataclass
class DeviceTier:
    """One tier of a vertically-stacked device (CFET/M3D) -- e.g. a CFET's
    stacked n-on-p (or p-on-n) channel pair. Added 2026-07-22 alongside
    `DeviceGeometry.stacked_tiers` below; see that field's docstring for
    what this does and doesn't represent yet.
    """
    channel_material_id: str
    channel_thickness_nm: float
    carrier_type: str  # "electron" | "hole"


@dataclass
class DeviceGeometry:
    channel_length_nm: float
    channel_width_nm: float
    channel_thickness_nm: float
    gate_oxide_thickness_nm: float
    gate_oxide_material_id: str
    channel_material_id: str
    substrate_material_id: str | None = None
    contact_metal: str | None = None
    doping_profile: dict[str, Any] | None = None  # escape hatch for DEVSIM
    # Added 2026-07-22 (standards-audit follow-up): makes CFET/GAA/M3D
    # geometries *representable* in the schema -- no backend actually
    # consumes gate_type/stacked_tiers yet (a real multi-tier/multi-gate
    # solver is separate, future work). "single" + None (the defaults)
    # matches every existing real case exactly; this is additive-only.
    gate_type: str = "single"  # "single" | "double" | "gate_all_around"
    stacked_tiers: list[DeviceTier] | None = None  # None -> today's only real case (planar single-tier)


@dataclass
class TransportResult:
    device_geometry: DeviceGeometry
    ion_uA_per_um: float
    ioff_uA_per_um: float
    subthreshold_swing_mV_dec: float
    mobility_cm2_Vs: float
    contact_resistance_ohm_um: float
    power_density_W_per_um2: float
    iv_curve: list[tuple[float, float]]
    provenance: ProvenanceInfo
    # Added 2026-07-22: real device-characteristic extraction (see
    # transport/extraction.py). None from transport/stub.py -- its V_t is
    # an algebraic input, not a simulated curve, so real extraction doesn't
    # apply there. Populated by transport/kwant_backend.py, which now
    # sweeps V_gs at two V_ds points specifically to make DIBL computable.
    threshold_voltage_V: float | None = None
    dibl_mV_V: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)
