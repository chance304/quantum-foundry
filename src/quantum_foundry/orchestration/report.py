"""Renders a real PPA-Y (Power, Performance, Area, Yield) Pareto-matrix
report for a HeterostructureSearchResult -- added 2026-07-22 closing a gap
the standards audit flagged: pareto.py's multi-objective search was always
real, but had no dedicated report format, only plain CLI text.

Mirrors validation/report.py's render_markdown() pattern: a real Markdown
table, never hiding an excluded candidate (matches heterostructure.py's own
"never silently drop an incomplete-data candidate" discipline).
"""
from __future__ import annotations

from .heterostructure import CandidateResult, HeterostructureSearchResult


def _row(candidate: CandidateResult, front: list) -> str:
    if candidate.pipeline_result is None:
        return f"{candidate.material_id} | — | — | — | — | no | {candidate.excluded_reason}"
    r = candidate.pipeline_result
    on_front = "yes" if r in front else "no"
    return (
        f"{candidate.material_id} | {r.transport_result.ion_uA_per_um:.3g} | "
        f"{r.transport_result.subthreshold_swing_mV_dec:.1f} | "
        f"{r.thermal_result.max_junction_temp_C:.1f} | "
        f"{r.yield_result.yield_fraction:.3f} | {on_front} | —"
    )


def _role_table(role_name: str, candidates: list[CandidateResult], front: list, recommended: str | None) -> list[str]:
    lines = [
        f"## {role_name} role",
        "",
        "Material | Ion (uA/um) | SS (mV/dec) | Tj (C) | Yield | Pareto front? | Excluded reason",
        "---|---|---|---|---|---|---",
    ]
    for c in candidates:
        lines.append(_row(c, front))
    lines.append("")
    if recommended:
        lines.append(f"**Recommendation:** `{recommended}` (sole Pareto-front member).")
    else:
        lines.append(
            f"**Recommendation:** none — {len(front)} candidate(s) on the Pareto front, "
            f"a real trade-off rather than a fabricated single winner."
        )
    return lines


def render_ppa_y_markdown(result: HeterostructureSearchResult) -> str:
    lines = ["# PPA-Y Pareto-Matrix Report", ""]
    lines += _role_table("n-type", result.n_candidates, result.n_pareto_front, result.recommended_n_material_id)
    lines.append("")
    lines += _role_table("p-type", result.p_candidates, result.p_pareto_front, result.recommended_p_material_id)
    lines.append("")
    lines.append(f"_Generated {result.generated_at.isoformat()}_")
    return "\n".join(lines) + "\n"
