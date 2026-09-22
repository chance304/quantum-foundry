"""Live C2DB source. C2DB is distributed as downloadable ASE (.db) database
files from cmr.fysik.dtu.dk, not a simple REST API — this module downloads
the relevant .db snapshot (cached locally) and queries it with ase.db.

NOT YET RUN as an automated fetch in this session either — fetch_material()
below (the ase.db-based path) remains unexecuted/unverified. What WAS done
2026-07-28: directly read C2DB's actual current live site by hand
(c2db.fysik.dtu.dk's real /table?filter= search and /material/<id> detail
pages — the site itself works fine, HTTP 200, confirmed via curl) to seed
mote2_monolayer.yaml/wte2_monolayer.yaml with real data. This surfaced two
real bugs in this module's own prior assumptions, neither ever exercised
before now:
  1. C2DB_DB_URL below (cmr.fysik.dtu.dk/c2db/c2db.db) is stale — that
     whole cmr.fysik.dtu.dk/c2db/ path now redirects to 2dhub.org. The
     real, working site root is https://c2db.fysik.dtu.dk/ (no /c2db/
     path segment) — confirmed live 2026-07-28, but its .db download
     endpoint (if one still exists at this URL) was NOT verified — only
     the HTML search/detail pages were read directly.
  2. The C2DB_UID naming convention guessed below ("MoS2-MoS2" style) does
     NOT match real uids seen on the live site: MoTe2/WTe2's actual C2DB
     uids are formula+hash strings like "MoTe2-38a53176109a" (the site's
     own "Old uid" field), not "<Formula>-<Formula>". The 3 pre-existing
     guessed entries below are UNCONFIRMED against this real pattern —
     don't trust them without checking the live site the same way.
See docs/DECISIONS.md 2026-07-28 for the full story.

Requires: pip install ase
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ..schema import Citation
from ._yaml_merge import merge_field

SEED_DATA_DIR = Path(__file__).parent / "seed_data"
CACHE_DIR = Path(__file__).parent / ".cache"

# C2DB names monolayers by prototype, e.g. "MoS2-MoS2" for the H-phase
# monolayer — an UNCONFIRMED guess (see module docstring above; real uids
# observed on the live site 2026-07-28 look like "MoTe2-38a53176109a",
# not this pattern). Still unverified against a downloaded .db file.
C2DB_UID = {
    "MoS2_monolayer": "MoS2-MoS2",
    "WSe2_monolayer": "WSe2-WSe2",
    "WS2_monolayer": "WS2-WS2",  # unverified — see docs/ROADMAP.md open item
}

# C2DB .db download endpoint — STALE, do not use as-is: this whole
# cmr.fysik.dtu.dk/c2db/ path redirects to 2dhub.org as of 2026-07-28 (see
# module docstring). The real live site root is https://c2db.fysik.dtu.dk/
# but its .db (if any) endpoint was not identified/verified this session —
# mote2_monolayer.yaml/wte2_monolayer.yaml were seeded by reading the
# site's HTML pages directly instead of going through this module.
C2DB_DB_URL = "https://cmr.fysik.dtu.dk/c2db/c2db.db"

FIELD_MAP = {
    "band_gap_eV": "gap",
    "work_function_eV": "work_function",
}


def _ensure_db() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    db_path = CACHE_DIR / "c2db.db"
    if not db_path.exists():
        import urllib.request

        urllib.request.urlretrieve(C2DB_DB_URL, db_path)
    return db_path


def fetch_material(material_id: str) -> dict:
    import ase.db

    uid = C2DB_UID[material_id]
    db_path = _ensure_db()
    db = ase.db.connect(str(db_path))
    row = db.get(uid=uid)

    citation = Citation(
        source="C2DB",
        identifier=uid,
        url=f"https://cmr.fysik.dtu.dk/c2db/c2db.html#{uid}",
        verified=False,  # not fetched/confirmed in this session
    )
    fields = {}
    for our_field, c2db_key in FIELD_MAP.items():
        value = row.get(c2db_key)
        if value is not None:
            fields[our_field] = float(value)
    return {"fields": fields, "citation": citation}


def refresh() -> None:
    SEED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for material_id in C2DB_UID:
        try:
            result = fetch_material(material_id)
        except Exception as exc:  # noqa: BLE001 — report and continue, don't fabricate
            print(f"  SKIPPED {material_id}: {exc}")
            continue
        merge_field(SEED_DATA_DIR, material_id, result["fields"], result["citation"])
        print(f"  merged C2DB fields for {material_id}: {list(result['fields'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.refresh:
        refresh()
