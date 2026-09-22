"""Renders the validation report — the artifact that shows measured-vs-simulated accuracy.

Usable from day one: entries with simulated=None render as "not yet
simulated" rather than being hidden, so the report is honest about progress
at any point in the build, not just at the end.
"""
from __future__ import annotations

from .compute import compute_agreement
from .registry import BenchmarkRegistry


def _format_citation(citation) -> str:
    doi_part = f", doi:{citation.doi}" if citation.doi else ""
    unverified = " *(unverified — not yet confirmed against the actual paper)*" if not citation.verified else ""
    return (
        f"{citation.authors} ({citation.year}), *{citation.title}*, {citation.venue}"
        f"{doi_part} — {citation.figure_or_table_ref}{unverified}"
    )


def render_markdown(registry: BenchmarkRegistry) -> str:
    lines = [
        "# Validation Report",
        "",
        "Quantity | Experimental (cited) | Simulated | %-error | Verdict",
        "---|---|---|---|---",
    ]
    for entry in sorted(registry.all_entries(), key=lambda e: e.id):
        exp = entry.experimental
        agreement = compute_agreement(entry)

        exp_cell = f"{exp.value} {exp.unit} — {_format_citation(exp.citation)}"

        if entry.simulated is None:
            sim_cell = "—"
            pct_cell = "—"
        else:
            stub_flag = " *(stub)*" if entry.simulated.provenance.is_stub else " *(real)*"
            sim_cell = f"{entry.simulated.value} {entry.simulated.unit}{stub_flag}"
            pct_cell = f"{agreement.pct_error:.1f}%" if agreement.pct_error is not None else "—"

        lines.append(f"{exp.quantity} | {exp_cell} | {sim_cell} | {pct_cell} | {agreement.verdict}")

    return "\n".join(lines) + "\n"
