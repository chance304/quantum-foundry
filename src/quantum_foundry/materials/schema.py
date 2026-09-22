"""Materials database schema.

MaterialRecord carries per-field Citation objects so every non-computed
constant traces to a named source — never presented as fact without one
(see CLAUDE.md's "one rule that matters most").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Citation:
    source: str                        # "JARVIS-DFT" | "C2DB" | "Materials Project" | named paper
    identifier: str                    # JVASP-id, C2DB uid, MP-id, or DOI
    year: int | None = None
    figure_or_table_ref: str | None = None
    url: str | None = None
    verified: bool = True              # False if hand-entered from a search summary, not fetched/read directly


@dataclass(frozen=True)
class MaterialRecord:
    material_id: str                              # canonical key, e.g. "MoS2_monolayer"
    formula: str
    # `lattice_constant_angstrom` assumes a single scalar (a=b), which only
    # holds for hexagonal 2D materials (the TMDs this project centers on).
    # Monoclinic bulk oxides (HfO2, ZrO2 gate dielectrics) have independent
    # a/b/c/beta parameters that don't reduce to one number — those go in
    # `extra["lattice_parameters"]` instead, with this field left None.
    # Discovered while seeding HfO2/ZrO2 real data (2026-07-20) — logged in
    # docs/DECISIONS.md rather than silently worked around.
    lattice_constant_angstrom: float | None = None
    band_gap_eV: float | None = None
    effective_mass_electron: float | None = None   # units of m0, in-plane
    effective_mass_hole: float | None = None        # units of m0, in-plane
    dielectric_constant: float | None = None
    thermal_conductivity_W_mK: float | None = None
    # Volumetric specific heat capacity, J/(m^3*K). Added 2026-07-22 -- no
    # seeded material has a real value yet (out of scope for the schema
    # addition itself); `thermal/hotspot_backend.py` used a hardcoded
    # silicon-order-of-magnitude default for every layer before this field
    # existed, since there was nowhere to look one up. See docs/ROADMAP.md.
    specific_heat_capacity_J_per_m3K: float | None = None
    work_function_eV: float | None = None
    citations: dict[str, Citation] = field(default_factory=dict)  # keyed by field name
    extra: dict[str, Any] = field(default_factory=dict)

    def citation_for(self, field_name: str) -> Citation | None:
        return self.citations.get(field_name)
