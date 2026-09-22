"""Ab-initio layer result types."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..provenance import ProvenanceInfo


@dataclass
class TightBindingHandle:
    format: str  # "analytic_effective_mass" | "wannier90_hr" (M5)
    path: Path | None
    loader: Callable[[], Any]


@dataclass
class DFTResult:
    material_id: str
    band_gap_eV: float
    # Optional as of 2026-07-22: dft/stub.py's gate is carrier-role-aware --
    # a run requested for one carrier role only requires that role's mass,
    # so the other may legitimately be None here (see dft/stub.py).
    effective_mass_electron: float | None
    effective_mass_hole: float | None
    lattice_constant_angstrom: float
    tight_binding_hamiltonian: TightBindingHandle | None
    provenance: ProvenanceInfo
    extra: dict[str, Any] = field(default_factory=dict)
