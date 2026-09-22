"""MaterialsDB: loads MaterialRecord entries from seed_data/*.yaml.

Cached YAML snapshots are refreshed from the live sources (JARVIS-DFT, C2DB,
Materials Project) via scripts/fetch_materials_seed_data.sh — this registry
only reads what's already on disk, it doesn't call any live API itself.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .citations import assert_citations_complete
from .schema import Citation, MaterialRecord

_SEED_DATA_DIR = Path(__file__).parent / "sources" / "seed_data"


class MaterialNotFoundError(KeyError):
    """Raised when a requested material_id has no seed data on disk."""


def _record_from_dict(data: dict) -> MaterialRecord:
    citations = {
        field_name: Citation(**citation_data)
        for field_name, citation_data in data.get("citations", {}).items()
    }
    return MaterialRecord(
        material_id=data["material_id"],
        formula=data["formula"],
        lattice_constant_angstrom=data.get("lattice_constant_angstrom"),
        band_gap_eV=data.get("band_gap_eV"),
        effective_mass_electron=data.get("effective_mass_electron"),
        effective_mass_hole=data.get("effective_mass_hole"),
        dielectric_constant=data.get("dielectric_constant"),
        thermal_conductivity_W_mK=data.get("thermal_conductivity_W_mK"),
        work_function_eV=data.get("work_function_eV"),
        citations=citations,
        extra=data.get("extra", {}),
    )


class MaterialsDB:
    def __init__(self, seed_data_dir: Path | None = None, *, enforce_citations: bool = True):
        self._dir = seed_data_dir or _SEED_DATA_DIR
        self._enforce_citations = enforce_citations
        self._records: dict[str, MaterialRecord] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self._dir.exists():
            return
        for path in sorted(self._dir.glob("*.yaml")):
            with path.open() as f:
                data = yaml.safe_load(f)
            record = _record_from_dict(data)
            if self._enforce_citations:
                assert_citations_complete(record)
            self._records[record.material_id] = record

    def get(self, material_id: str) -> MaterialRecord:
        try:
            return self._records[material_id]
        except KeyError:
            raise MaterialNotFoundError(
                f"No seed data for material_id={material_id!r}. "
                f"Available: {sorted(self._records)}"
            ) from None

    def __contains__(self, material_id: str) -> bool:
        return material_id in self._records

    def list_ids(self) -> list[str]:
        return sorted(self._records)
