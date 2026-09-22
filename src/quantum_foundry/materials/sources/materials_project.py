"""Live Materials Project source, for gate dielectrics (HfO2, ZrO2) — the
one source in this project requiring an API key (MP_API_KEY env var, per
scripts/fetch_materials_seed_data.sh).

mp-352 (HfO2, monoclinic) and mp-2858 (ZrO2, monoclinic) were verified this
session by direct fetch of their materialsproject.org pages (band gap,
density, dielectric constants — see docs/DECISIONS.md,
2026-07-20). This module is the real programmatic path (mp-api client) for
refreshing that data going forward; the fields/summary keys below match the
mp-api SummaryDoc schema as of this session's knowledge — verify against the
installed mp-api version before relying on it.

Requires: pip install mp-api
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from ..schema import Citation
from ._yaml_merge import merge_field

SEED_DATA_DIR = Path(__file__).parent / "seed_data"

# Verified real via direct fetch this session.
MP_ID = {
    "HfO2": "mp-352",
    "ZrO2": "mp-2858",
}

FIELD_MAP = {
    "band_gap_eV": "band_gap",
    "dielectric_constant": "e_total",  # polycrystalline total dielectric constant
}


def fetch_material(material_id: str, api_key: str) -> dict:
    from mp_api.client import MPRester

    mp_id = MP_ID[material_id]
    with MPRester(api_key) as mpr:
        doc = mpr.summary.search(material_ids=[mp_id])[0]

    citation = Citation(
        source="Materials Project",
        identifier=mp_id,
        url=f"https://materialsproject.org/materials/{mp_id}",
        verified=True,
    )
    fields = {}
    for our_field, mp_key in FIELD_MAP.items():
        value = getattr(doc, mp_key, None)
        if value is not None:
            fields[our_field] = float(value)
    return {"fields": fields, "citation": citation}


def refresh() -> None:
    api_key = os.environ.get("MP_API_KEY")
    if not api_key:
        print("  MP_API_KEY not set — skipping Materials Project refresh.")
        return
    SEED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for material_id in MP_ID:
        result = fetch_material(material_id, api_key)
        merge_field(SEED_DATA_DIR, material_id, result["fields"], result["citation"])
        print(f"  merged Materials Project fields for {material_id}: {list(result['fields'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.refresh:
        refresh()
