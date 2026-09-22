"""Best-effort NGMM-style materials-library export.

Reshapes MaterialRecord (materials/schema.py, already real and cited) into a
format inspired by NGMM's 3D-ADK architecture description. See
disclaimers.NGMM_SCHEMA_DISCLAIMER — never claim compatibility with a real
NGMM/TIE schema, since it isn't public.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..materials.registry import MaterialsDB
from ..materials.schema import MaterialRecord
from .disclaimers import (
    NGMM_MATERIALS_LIST_CAVEAT,
    NGMM_SCHEMA_DISCLAIMER,
    NGMM_SUPPORTED_MATERIALS,
)
from .packaging_open_questions import packaging_compatibility_note

# field name -> unit label. Same field set as MaterialRecord, just reshaped
# with units + citation confidence attached.
_FIELD_UNITS: dict[str, str | None] = {
    "lattice_constant_angstrom": "Å",
    "band_gap_eV": "eV",
    "effective_mass_electron": "m0",
    "effective_mass_hole": "m0",
    "dielectric_constant": None,
    "thermal_conductivity_W_mK": "W/(m·K)",
    "work_function_eV": "eV",
}


@dataclass(frozen=True)
class NGMMPropertyValue:
    value: Any
    unit: str | None
    citation_source: str | None
    citation_identifier: str | None
    citation_verified: bool  # propagated from Citation.verified — never upgraded


@dataclass(frozen=True)
class NGMMMaterialLibraryEntry:
    name: str
    formula: str
    on_ngmm_supported_materials_list: bool
    properties: dict[str, NGMMPropertyValue]
    extra: dict[str, Any] = field(default_factory=dict)
    schema_disclaimer: str = NGMM_SCHEMA_DISCLAIMER


@dataclass(frozen=True)
class NGMMMaterialLibrary:
    entries: list[NGMMMaterialLibraryEntry]
    generated_at: datetime
    schema_disclaimer: str = NGMM_SCHEMA_DISCLAIMER
    materials_list_caveat: str = NGMM_MATERIALS_LIST_CAVEAT


def export_material(record: MaterialRecord) -> NGMMMaterialLibraryEntry:
    properties: dict[str, NGMMPropertyValue] = {}
    for field_name, unit in _FIELD_UNITS.items():
        value = getattr(record, field_name)
        if value is None:
            continue
        citation = record.citation_for(field_name)
        properties[field_name] = NGMMPropertyValue(
            value=value,
            unit=unit,
            citation_source=citation.source if citation else None,
            citation_identifier=citation.identifier if citation else None,
            citation_verified=citation.verified if citation else False,
        )

    extra = dict(record.extra)  # copy — never mutate the source record
    extra["packaging_compatibility"] = packaging_compatibility_note(record.material_id, record.formula)

    return NGMMMaterialLibraryEntry(
        name=record.material_id,
        formula=record.formula,
        on_ngmm_supported_materials_list=record.formula in NGMM_SUPPORTED_MATERIALS,
        properties=properties,
        extra=extra,
    )


def export_material_library(
    db: MaterialsDB, material_ids: list[str] | None = None
) -> NGMMMaterialLibrary:
    ids = material_ids if material_ids is not None else db.list_ids()
    entries = [export_material(db.get(mid)) for mid in ids]
    return NGMMMaterialLibrary(entries=entries, generated_at=datetime.now(UTC))
