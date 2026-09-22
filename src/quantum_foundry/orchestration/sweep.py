"""Generic, material-agnostic parameter sweep. Reused as-is by M6's
heterostructure.py (n/p-asymmetry search) — not modified for that purpose.
"""
from __future__ import annotations

import copy

from .config import RunConfig
from .pipeline import Pipeline, PipelineResult


def sweep(
    base_config: RunConfig,
    stage: str,
    param: str,
    values: list,
    pipeline: Pipeline | None = None,
) -> list[PipelineResult]:
    pipeline = pipeline or Pipeline()
    results = []
    for value in values:
        cfg = copy.deepcopy(base_config)
        getattr(cfg, stage).params[param] = value
        results.append(pipeline.run(cfg))
    return results
