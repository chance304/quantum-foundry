"""Shared read-modify-write helper for source modules writing into
seed_data/<material_id>.yaml — merges new fields/citations into whatever
another source already wrote, rather than overwriting the whole file.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from ..schema import Citation


def merge_field(
    seed_data_dir: Path,
    material_id: str,
    fields: dict[str, float],
    citation: Citation,
    extra_fields: dict[str, Any] | None = None,
) -> None:
    """Merge `fields` (each citing the same `citation`) into <material_id>.yaml.

    `extra_fields`, if given, merges per-key into the file's `extra` dict
    (not a wholesale replacement -- sibling `extra` keys another source
    already wrote are left untouched) -- for anisotropic materials whose
    real data (lattice_parameters, effective_mass_tensor, ...) doesn't fit
    this schema's scalar fields. Each extra_fields key gets its own citation
    entry too, same discipline as the flat fields above.
    """
    path = seed_data_dir / f"{_slug(material_id)}.yaml"
    data: dict[str, Any] = {}
    if path.exists():
        with path.open() as f:
            data = yaml.safe_load(f) or {}

    data.setdefault("material_id", material_id)
    data.setdefault("citations", {})

    for field_name, value in fields.items():
        data[field_name] = value
        data["citations"][field_name] = asdict(citation)

    if extra_fields:
        data.setdefault("extra", {})
        for key, value in extra_fields.items():
            data["extra"][key] = value
            data["citations"][key] = asdict(citation)

    with path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def _slug(material_id: str) -> str:
    return material_id.lower().replace("-", "_")
