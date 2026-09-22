"""Manufacturability/yield layer result types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..provenance import ProvenanceInfo


@dataclass
class YieldResult:
    yield_fraction: float
    defect_density_per_cm2: float
    critical_area_um2: float | None
    model: str  # "trivial_linear" | "poisson" | "murphy" | "negative_binomial" | "monte_carlo"
    confidence_interval: tuple[float, float] | None
    provenance: ProvenanceInfo
    extra: dict[str, Any] = field(default_factory=dict)
