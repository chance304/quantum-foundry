"""Single source of truth for every NGMM-compatibility-layer disclaimer.

Every export in ngmm_compat/ carries this wording, verbatim, wherever a
disclaimer field appears — so the caveat can never quietly drift or get
dropped in one export but not another.

Background (verified 2026-07-20 against two real DARPA source PDFs, both
"Distribution Statement A: Approved for public release; distribution
unlimited" — DARPA-SN-26-69 and an NGMM Program Update deck): NGMM's real
material-library / chiplet-collateral schema is owned by TIE (Texas
Institute for Electronics) as part of their "TNC Interface PDK" and is not
public. Nothing in this package has been verified against that real schema.
See docs/NGMM_COMPATIBILITY.md for full context.
"""
from __future__ import annotations

NGMM_SCHEMA_DISCLAIMER = (
    "This is quantum-foundry's own best-effort, standards-inspired export format. "
    "NGMM's real material-library / chiplet-collateral schema (owned by TIE / the "
    "TNC Interface PDK) is not public. This export has NOT been verified against any "
    "real NGMM or TIE schema and must not be represented as compatible with one."
)

# NGMM's own stated supported-materials list (from the NGMM Program Update deck,
# 2026-07-20). None of quantum-foundry's currently seeded materials are on it.
NGMM_SUPPORTED_MATERIALS: tuple[str, ...] = (
    "Si", "glass", "GaN", "InP", "GaAs", "SiC", "ferrite", "HgCdTe",
)

NGMM_MATERIALS_LIST_CAVEAT = (
    "quantum-foundry's seeded materials (2D TMDs + gate oxides) are NOT on NGMM's "
    "own stated supported-materials list. This export demonstrates format-level "
    "plumbing only — it is not a claim that these materials are accepted into, or "
    "compatible with, any real NGMM process."
)
