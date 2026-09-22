"""Generic, material-agnostic Pareto front. Reused as-is by M6's
heterostructure.py (n/p-asymmetry search) — not modified for that purpose.
"""
from __future__ import annotations

from collections.abc import Callable

from .pipeline import PipelineResult


def pareto_front(
    results: list[PipelineResult],
    objectives: dict[str, Callable[[PipelineResult], float]],
    minimize: set[str],
) -> list[PipelineResult]:
    """`objectives` maps a name to an extractor fn; `minimize` names which
    objectives should be minimized (others maximized)."""

    def dominates(a: PipelineResult, b: PipelineResult) -> bool:
        at_least_as_good, strictly_better = True, False
        for name, extractor in objectives.items():
            va, vb = extractor(a), extractor(b)
            better = va <= vb if name in minimize else va >= vb
            if not better:
                at_least_as_good = False
            if va != vb and better:
                strictly_better = True
        return at_least_as_good and strictly_better

    return [r for r in results if not any(dominates(o, r) for o in results if o is not r)]
