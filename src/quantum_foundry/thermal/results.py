"""Thermal/mechanical layer result types."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..provenance import ProvenanceInfo


@dataclass
class ThermalLayer:
    material_id: str
    thickness_nm: float
    role: str  # "channel" | "gate_oxide" | "substrate" | "contact_metal"


@dataclass
class MaterialStack:
    layers: list[ThermalLayer]


@dataclass
class FieldHandle:
    format: str  # "xdmf_hdf5" | "lumped_scalar" | "hotspot_grid_steady"
    path: Path | None
    loader: Callable[[], Any]


@dataclass
class ThermalResult:
    max_junction_temp_C: float
    thermal_resistance_K_per_W: float
    stress_MPa: float | None
    field_handle: FieldHandle | None
    provenance: ProvenanceInfo
    extra: dict[str, Any] = field(default_factory=dict)
