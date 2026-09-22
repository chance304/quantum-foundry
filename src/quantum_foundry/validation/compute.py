"""%-error / agreement computation between a benchmark's experimental and
simulated values.
"""
from __future__ import annotations

from .schema import AgreementResult, BenchmarkEntry

# pct_error buckets -> verdict. Thresholds are a starting point, not a
# claimed industry standard — revisit once real solver output exists to
# calibrate against (M3/M5).
DEFAULT_THRESHOLDS = {
    "excellent": 10.0,   # <= 10% error
    "reasonable": 30.0,  # <= 30% error
    # anything above "reasonable" is "poor"
}


def _bucket(pct_error: float, thresholds: dict[str, float]) -> str:
    if pct_error <= thresholds["excellent"]:
        return "excellent"
    if pct_error <= thresholds["reasonable"]:
        return "reasonable"
    return "poor"


def compute_agreement(
    entry: BenchmarkEntry,
    thresholds: dict[str, float] | None = None,
) -> AgreementResult:
    if entry.simulated is None:
        return AgreementResult(entry.id, None, None, "not yet simulated")

    exp = entry.experimental.value
    sim = entry.simulated.value

    if exp == 0:
        # Avoid a ZeroDivisionError silently producing a misleading verdict —
        # surface this as an explicit, distinct case instead.
        return AgreementResult(entry.id, None, None, "undefined (experimental value is zero)")

    pct_error = abs(sim - exp) / abs(exp) * 100

    within_uncertainty = None
    uncertainty = entry.experimental.uncertainty
    if uncertainty is not None:
        within_uncertainty = abs(sim - exp) <= uncertainty

    verdict = _bucket(pct_error, thresholds or DEFAULT_THRESHOLDS)
    return AgreementResult(entry.id, pct_error, within_uncertainty, verdict)
