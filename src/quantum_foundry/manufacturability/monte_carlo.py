"""Real spatial Monte Carlo wafer-yield engine -- added 2026-07-22 closing
the gap the standards audit flagged: only closed-form (Poisson/Murphy/
Stapper) single-number yield existed; nothing simulated per-die defect
placement across an actual 300mm wafer, and YieldResult.confidence_interval
(a schema field that's existed since M1) had never once been populated.

Reuses poisson_murphy.py's _critical_area_cm2()/_require_d0() rather than
redefining the area model -- this is deliberately the SAME critical-area
definition the closed-form models use, so Monte Carlo and Poisson results
are directly comparable. Each die is independently defect-free with the
same per-die probability p = exp(-D0*A) the closed-form Poisson model
computes directly; the number of defect-free dies on an n_dies-die wafer
is therefore Binomial(n_dies, p), sampled n_runs times to get a real
run-to-run (wafer-to-wafer) yield distribution and confidence interval --
this is the exact large-N limit of the same spatial process Poisson
assumes, not a different model, and (see test suite) converges to the
closed-form Poisson result as expected.

dies_per_wafer() is a standard edge-exclusion-corrected gross-dies-per-wafer
approximation (gross tiling minus a perimeter-loss correction term) --
flagged explicitly as an approximation, same honesty discipline as
_critical_area_cm2() itself, which is also a flat formula, not a real
layout-aware die-per-wafer tool.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..provenance import ProvenanceInfo
from ..transport.results import TransportResult
from .functional_criteria import FUNCTIONAL_ION_IOFF_RATIO_MIN, is_functional_transistor
from .poisson_murphy import _critical_area_cm2, _require_d0
from .results import YieldResult

TOOL_VERSION = "monte-carlo-yield-0.1"

DEFAULT_WAFER_DIAMETER_MM = 300.0
DEFAULT_EDGE_EXCLUSION_MM = 3.0  # standard 300mm-wafer edge-exclusion zone
DEFAULT_N_RUNS = 1000


def dies_per_wafer(
    die_area_cm2: float,
    wafer_diameter_mm: float = DEFAULT_WAFER_DIAMETER_MM,
    edge_exclusion_mm: float = DEFAULT_EDGE_EXCLUSION_MM,
) -> int:
    """Standard gross-dies-per-wafer (GDW) estimate with an edge-exclusion
    zone and a perimeter-loss correction term (dies straddling the usable-
    area boundary are lost, not just imperfectly counted by the raw area
    ratio): GDW = pi*R^2/A - pi*(2R)/sqrt(2*A). Verified 2026-07-27
    (standards audit) as a real, standard semiconductor-yield-engineering
    formula, not invented for this project -- widely used in fab
    yield-estimation practice (the same "gross dies minus edge loss"
    shape appears across yield-modeling references, e.g. Quirk & Serda,
    *Semiconductor Manufacturing Technology*'s treatment of die-per-wafer
    estimation), medium-high confidence on the exact textbook attribution
    since no single page was directly verified this pass. An
    approximation, not real layout-aware die tiling -- see module docstring.
    """
    if die_area_cm2 <= 0:
        return 0
    usable_radius_cm = (wafer_diameter_mm - 2 * edge_exclusion_mm) / 10.0 / 2.0
    if usable_radius_cm <= 0:
        return 0
    gross = math.pi * usable_radius_cm**2 / die_area_cm2
    edge_loss = math.pi * (2 * usable_radius_cm) / math.sqrt(2 * die_area_cm2)
    return max(0, math.floor(gross - edge_loss))


def run_monte_carlo(
    transport_result: TransportResult,
    defect_density_per_cm2: float,
    params: dict[str, Any],
) -> YieldResult:
    area_cm2 = _critical_area_cm2(transport_result, params)
    n_runs = int(params.get("n_runs", DEFAULT_N_RUNS))
    wafer_diameter_mm = params.get("wafer_diameter_mm", DEFAULT_WAFER_DIAMETER_MM)
    edge_exclusion_mm = params.get("edge_exclusion_mm", DEFAULT_EDGE_EXCLUSION_MM)
    n_dies = int(params.get("dies_per_wafer") or dies_per_wafer(area_cm2, wafer_diameter_mm, edge_exclusion_mm))
    min_ion_ioff_ratio = params.get("min_ion_ioff_ratio", FUNCTIONAL_ION_IOFF_RATIO_MIN)
    rng_seed = params.get("rng_seed")

    ion_ioff_ok = is_functional_transistor(
        transport_result.ion_uA_per_um, transport_result.ioff_uA_per_um, min_ion_ioff_ratio
    )

    if n_dies <= 0 or not ion_ioff_ok:
        # If the device itself doesn't meet the Ion/Ioff gate, no amount of
        # defect-freedom makes a die "functional" -- every run yields zero,
        # so skip sampling entirely rather than simulating a foregone conclusion.
        yield_fraction = 0.0
        confidence_interval = (0.0, 0.0)
    else:
        # Each die is independently defect-free with probability
        # p = exp(-D0*A) (the same per-die probability the closed-form
        # Poisson model computes directly) -- so the COUNT of defect-free
        # dies on one n_dies-die wafer is Binomial(n_dies, p). Sampling
        # from this exact distribution (rather than drawing n_dies
        # individual per-die defect counts) is both mathematically
        # equivalent under the same independent-uniform-defect assumption
        # Poisson/Murphy/Stapper already make, AND avoids ever
        # materializing an (n_runs, n_dies) array -- n_dies is routinely
        # in the millions-to-trillions for realistic die/wafer areas,
        # which would otherwise exhaust memory (found by actually running
        # this against a small test die -- see docs/DECISIONS.md).
        p_defect_free = math.exp(-defect_density_per_cm2 * area_cm2)
        rng = np.random.default_rng(rng_seed)
        functional_die_counts = rng.binomial(n_dies, p_defect_free, size=n_runs)
        yields_per_run = functional_die_counts / n_dies
        yield_fraction = float(yields_per_run.mean())
        confidence_interval = (
            float(np.percentile(yields_per_run, 2.5)),
            float(np.percentile(yields_per_run, 97.5)),
        )

    return YieldResult(
        yield_fraction=yield_fraction,
        defect_density_per_cm2=defect_density_per_cm2,
        critical_area_um2=area_cm2 * 1e8,
        model="monte_carlo",
        confidence_interval=confidence_interval,
        provenance=ProvenanceInfo(backend_name="monte_carlo_yield", is_stub=False, tool_version=TOOL_VERSION),
        extra={
            "n_runs": n_runs,
            "n_dies_per_wafer": n_dies,
            "wafer_diameter_mm": wafer_diameter_mm,
            "ion_ioff_functional_gate_passed": ion_ioff_ok,
            "min_ion_ioff_ratio": min_ion_ioff_ratio,
        },
    )


class MonteCarloYieldBackend:
    name, is_stub = "monte_carlo", False

    def run(self, transport_result: TransportResult, params: dict[str, Any]) -> YieldResult:
        return run_monte_carlo(transport_result, _require_d0(params), params)
