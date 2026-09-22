"""Bonding/packaging-compatibility placeholder for the NGMM export layer only.

Deliberately NOT part of materials/schema.py or the seed YAMLs: whether a
2D-material logic die can actually be Cu-Cu/hybrid-bonded or
thermocompression-bonded into an NGMM-style mixed-material 3D stack is a
real, unresolved *process*-compatibility question — categorically different
from the *measurement* gaps (like WS2_monolayer's null placeholder) the core
materials schema already handles. Kept confined here so it only ever shows
up in NGMM-facing exports, never silently blended into the core data model.

`status` is deliberately restricted to values that can never read as an
affirmative compatibility claim without a real citation — mirrors this
project's citation-completeness discipline (materials/citations.py) applied
to a process question instead of a measured constant.
"""
from __future__ import annotations

_BONDING_PROCESSES_CONSIDERED = ("Cu-Cu hybrid bonding", "thermocompression bonding")

_GENERIC_NOTE = (
    "Whether {formula} can be bonded into an NGMM-style mixed-material 3D stack "
    "is an open, unresolved question — not assessed by quantum-foundry, outside "
    "current device-level scope. Tracked in docs/ROADMAP.md, not silently assumed "
    "compatible."
)

# Empty on purpose — no seeded material has a real, cited answer yet.
_MATERIAL_SPECIFIC_NOTES: dict[str, str] = {}


def packaging_compatibility_note(material_id: str, formula: str) -> dict:
    return {
        "status": "unresolved_open_question",
        "bonding_processes_considered": list(_BONDING_PROCESSES_CONSIDERED),
        "note": _MATERIAL_SPECIFIC_NOTES.get(material_id, _GENERIC_NOTE.format(formula=formula)),
        "verified": False,
    }
