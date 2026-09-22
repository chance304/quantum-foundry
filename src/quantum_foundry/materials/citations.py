"""Citation-completeness enforcement for MaterialRecord.

Every non-computed physical constant must cite a source (CLAUDE.md's core
rule). This module checks that, rather than trusting each seed file by hand.
"""
from __future__ import annotations

from .schema import MaterialRecord

# Fields that are physical constants requiring a citation when set.
# material_id/formula are identity fields, not measured/computed quantities.
CITABLE_FIELDS = (
    "lattice_constant_angstrom",
    "band_gap_eV",
    "effective_mass_electron",
    "effective_mass_hole",
    "dielectric_constant",
    "thermal_conductivity_W_mK",
    "work_function_eV",
)


class CitationCompletenessError(ValueError):
    """Raised when a MaterialRecord has a physical-constant field set with no citation."""


def missing_citations(record: MaterialRecord) -> list[str]:
    """Return field names that are set (non-None) but have no matching Citation."""
    missing = []
    for field_name in CITABLE_FIELDS:
        value = getattr(record, field_name)
        if value is not None and field_name not in record.citations:
            missing.append(field_name)
    return missing


def assert_citations_complete(record: MaterialRecord) -> None:
    missing = missing_citations(record)
    if missing:
        raise CitationCompletenessError(
            f"MaterialRecord '{record.material_id}' has values with no citation: {missing}"
        )
