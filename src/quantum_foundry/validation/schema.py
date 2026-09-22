"""Validation/benchmark-reporting schema — what makes accuracy claims checkable.

Every ExperimentalValue cites a real paper/database entry. simulated stays
None until a matching pipeline run exists — the report renders that
explicitly as "not yet simulated" rather than hiding the gap.

SimulatedValue.uncertainty (added 2026-07-22, docs/STANDARDS_AUDIT.md Tier
2): schema parity with ExperimentalValue.uncertainty, `None` for every
result today -- no seeded value yet, same honest-None pattern as
MaterialRecord.specific_heat_capacity_J_per_m3K. Deliberately NOT paired
with a "verified" flag or any solver-convergence check here: no real
solver in this pipeline currently runs a mesh/mesh-independence study to
hang that on (Kwant's real backend is a single toy-lattice run; HotSpot's
grid resolution was found empirically). That real verification-vs-
validation distinction (ASME V&V 10/20) is M5's job -- see
docs/M5_PLAN.md's "Mesh convergence study" section, added the same day.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..provenance import ProvenanceInfo


@dataclass(frozen=True)
class Citation:
    authors: str
    year: int | None
    title: str
    venue: str
    doi: str | None
    figure_or_table_ref: str          # required — a benchmark without a locatable source isn't one
    url: str | None = None
    verified: bool = True              # False if not yet confirmed by reading the actual paper


@dataclass(frozen=True)
class ExperimentalValue:
    quantity: str                      # canonical name, e.g. "contact_resistance"
    value: float
    unit: str
    citation: Citation
    uncertainty: float | None = None
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulatedValue:
    quantity: str
    value: float
    unit: str
    provenance: ProvenanceInfo
    uncertainty: float | None = None
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkEntry:
    id: str
    experimental: ExperimentalValue
    simulated: SimulatedValue | None = None


@dataclass(frozen=True)
class AgreementResult:
    benchmark_id: str
    pct_error: float | None
    within_uncertainty: bool | None
    verdict: str  # "excellent" | "reasonable" | "poor" | "not yet simulated"
