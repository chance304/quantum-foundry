"""Live JARVIS-DFT source. Fetches real DFT-computed 2D-material properties
via the `jarvis-tools` package's figshare-hosted "dft_2d" dataset and
merges them (read-modify-write, preserving fields other sources already
wrote) into src/quantum_foundry/materials/sources/seed_data/<id>.yaml.

Verified 2026-07-20/21 against the *actual* dft_2d dataset content — not
just individual NIST-hosted pages, and not just jarvis-tools' documented
API surface. The dataset was downloaded directly from the same figshare URL
jarvis-tools' own source uses (https://ndownloader.figshare.com/files/38521268,
file d2-12-12-2022.json, confirmed by reading jarvis-tools' figshare.py on
GitHub rather than guessing a file ID) and parsed by hand to confirm field
semantics. This caught a real bug: effective mass is NOT a flat
avg_elec_mass/avg_hole_mass scalar usable as our in-plane value — that field
is the *average of the x, y, and z tensor components*, and for a layered 2D
material the z (out-of-plane, weak van-der-Waals-direction) component is
enormous and dominates the average, making it physically the wrong quantity
for a channel-transport effective mass. The real in-plane value lives in
effective_masses_300K.n[0]/.p[0] (an [x, y, z] triplet) — see
docs/DECISIONS.md for the full story. Confirmed real material_ids present
in this dataset: MoS2 (JVASP-664), graphene (JVASP-667), hBN (JVASP-688),
WS2 (JVASP-658, resolving a standing gap), black phosphorus (JVASP-5983,
anisotropic -- see its own seed YAML). MoTe2/WTe2 confirmed NOT present in
this dataset snapshot (checked by exact + regex formula match against all
1103 entries, not a single missed lookup).

Corrected 2026-07-22: WSe2 was previously (incorrectly) listed here as
JVASP-653 and included in JVASP_IDS below. Directly querying this dataset
confirmed JVASP-653 does NOT exist in it at all -- it's a real, live,
individually-hosted NIST page (used for WSe2's hand-seeded lattice/bandgap/
dielectric values), just not one included in this particular bulk snapshot.
The dataset instead has JVASP-652, a separate real WSe2 monolayer DFT run
with meaningfully different values for the same fields. WSe2_monolayer has
been removed from JVASP_IDS below (same treatment black_phosphorus used to
get, see next paragraph) so `refresh()` doesn't crash on it -- with no
per-item error handling, one LookupError previously would have silently
aborted the whole refresh() loop before it ever reached graphene/hBN/WS2.
See wse2_monolayer.yaml and docs/DECISIONS.md for how its
effective_mass_hole was sourced from JVASP-652 instead, cited as a distinct
DFT run rather than silently merged.

Anisotropic materials (added 2026-07-22): black_phosphorus_monolayer
(JVASP-5983) is genuinely anisotropic -- real a != b lattice, real
armchair-vs-zigzag effective-mass split -- so its scalar
lattice_constant_angstrom/effective_mass_electron/effective_mass_hole/
dielectric_constant fields are deliberately left None; the real data goes
into extra["lattice_parameters"]/extra["effective_mass_tensor"]/
extra["dielectric_tensor"] instead (see _ANISOTROPIC_MATERIAL_IDS and
_extract_fields() below). Field names/values confirmed 2026-07-22 against
the real installed jarvis-tools dataset (abc=[3.32246, 4.57864, ...],
effective_masses_300K.n=[1.31, 0.19, ...]/.p=[3.25, 0.16, ...],
epsx=3.0519/epsy=4.4231/epsz=2.0532), matching the pre-existing hand-seeded
black_phosphorus_monolayer.yaml to rounding.

`refresh()` is deliberately NOT run against the live seed file for
black_phosphorus as part of folding it in here -- merge_field() overwrites
each field's citation unconditionally, and the hand-seeded file's
band_gap_eV citation carries a figure_or_table_ref
("optb88vdw_bandgap") that a fresh auto-fetch citation lacks. This is a
pre-existing, already-accepted trade-off for the 4 materials already in
JVASP_IDS (not introduced by this change) -- black_phosphorus joining that
list inherits the same known limitation. See docs/ROADMAP.md/docs/DECISIONS.md.

Requires: pip install jarvis-tools (uses jarvis.db.figshare.data("dft_2d"),
the documented API -- not independently verified against a real install in
this session; the dataset content itself was verified via a direct
download+parse, bypassing jarvis-tools entirely, see above).
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..schema import Citation
from ._yaml_merge import merge_field

SEED_DATA_DIR = Path(__file__).parent / "seed_data"

# material_id -> JVASP id, for the materials this project seeds.
# All confirmed real by direct dataset download+parse this session (see
# module docstring) -- never guessed.
JVASP_IDS = {
    "MoS2_monolayer": "JVASP-664",
    "graphene_monolayer": "JVASP-667",
    "hBN_monolayer": "JVASP-688",
    "WS2_monolayer": "JVASP-658",
    "black_phosphorus_monolayer": "JVASP-5983",
    # WSe2_monolayer deliberately excluded here -- its primary source,
    # JVASP-653, is a real live NIST page but confirmed NOT present in this
    # dataset (only JVASP-652, a different DFT run, is); refresh()/
    # fetch_material() would raise LookupError for it. See module docstring
    # and wse2_monolayer.yaml.
}

# Materials whose real in-plane properties don't reduce to one isotropic
# scalar (a != b lattice, armchair-vs-zigzag mass/dielectric split) -- see
# module docstring. Extracted into extra[...] instead of the flat scalar
# fields below.
_ANISOTROPIC_MATERIAL_IDS = {"black_phosphorus_monolayer"}

# Field name in our schema -> key in the jarvis-tools dft_2d dataset record.
# "a"/"b" are read from atoms.abc (index 0/1), not a flat top-level field --
# handled specially in _extract_fields(), not via this simple map.
# dielectric_constant is skipped here for anisotropic materials (a lossy
# scalar) -- see _extract_fields().
FIELD_MAP = {
    "band_gap_eV": "optb88vdw_bandgap",
    "dielectric_constant": "epsx",
}


def _extract_fields(material_id: str, row: dict) -> dict[str, Any]:
    """Pure, network-free extraction of our schema's fields from one raw
    jarvis-tools dft_2d dataset row. Split out from fetch_material() so the
    anisotropic-vs-isotropic branching logic is unit-testable without
    jarvis-tools installed (it's an optional, non-dev dependency -- not in
    the lightweight CI job).
    """
    anisotropic = material_id in _ANISOTROPIC_MATERIAL_IDS

    fields: dict[str, float] = {}
    for our_field, jarvis_key in FIELD_MAP.items():
        if anisotropic and our_field == "dielectric_constant":
            continue  # -> extra["dielectric_tensor"] instead, see below
        if row.get(jarvis_key) not in (None, "na"):
            fields[our_field] = float(row[jarvis_key])

    extra_fields: dict[str, Any] = {}
    abc = row.get("atoms", {}).get("abc")
    masses = row.get("effective_masses_300K", {})
    n, p = masses.get("n"), masses.get("p")

    if anisotropic:
        if abc and abc[0] not in (None, "na") and abc[1] not in (None, "na"):
            extra_fields["lattice_parameters"] = {
                "a_angstrom": float(abc[0]),
                "b_angstrom": float(abc[1]),
            }
        tensor: dict[str, Any] = {}
        if isinstance(n, list) and n[0] not in (None, "na") and n[1] not in (None, "na"):
            tensor["electron"] = {"armchair_x": float(n[0]), "zigzag_y": float(n[1])}
        if isinstance(p, list) and p[0] not in (None, "na") and p[1] not in (None, "na"):
            tensor["hole"] = {"armchair_x": float(p[0]), "zigzag_y": float(p[1])}
        if tensor:
            extra_fields["effective_mass_tensor"] = tensor
        epsx, epsy, epsz = row.get("epsx"), row.get("epsy"), row.get("epsz")
        if all(v not in (None, "na") for v in (epsx, epsy, epsz)):
            assert epsx is not None and epsy is not None and epsz is not None
            extra_fields["dielectric_tensor"] = {
                "epsx_armchair": float(epsx),
                "epsy_zigzag": float(epsy),
                "epsz_out_of_plane": float(epsz),
            }
    else:
        # In-plane (x) component only -- see module docstring for why the
        # flat avg_elec_mass/avg_hole_mass fields are the wrong quantity.
        if abc and abc[0] not in (None, "na"):
            fields["lattice_constant_angstrom"] = float(abc[0])
        if isinstance(n, list) and n[0] not in (None, "na"):
            fields["effective_mass_electron"] = float(n[0])
        if isinstance(p, list) and p[0] not in (None, "na"):
            fields["effective_mass_hole"] = float(p[0])

    return {"fields": fields, "extra_fields": extra_fields}


def fetch_material(material_id: str) -> dict:
    """Fetch one material's record from the live jarvis-tools dft_2d dataset."""
    from jarvis.db.figshare import (
        data as jarvis_data,  # local import: heavy, optional dep
    )

    jvasp_id = JVASP_IDS[material_id]
    dataset = jarvis_data("dft_2d")
    match = next((row for row in dataset if row.get("jid") == jvasp_id), None)
    if match is None:
        raise LookupError(f"{jvasp_id} not found in jarvis-tools dft_2d dataset")

    citation = Citation(
        source="JARVIS-DFT",
        identifier=jvasp_id,
        url=f"https://www.ctcms.nist.gov/~knc6/jsmol/{jvasp_id}.html",
        verified=True,
    )
    extracted = _extract_fields(material_id, match)
    return {
        "fields": extracted["fields"],
        "extra_fields": extracted["extra_fields"],
        "citation": citation,
    }


def refresh() -> None:
    SEED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for material_id in JVASP_IDS:
        result = fetch_material(material_id)
        merge_field(
            SEED_DATA_DIR,
            material_id,
            result["fields"],
            result["citation"],
            result["extra_fields"] or None,
        )
        merged = list(result["fields"]) + list(result["extra_fields"])
        print(f"  merged JARVIS-DFT fields for {material_id}: {merged}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.refresh:
        refresh()
