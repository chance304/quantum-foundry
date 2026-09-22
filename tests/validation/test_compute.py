from quantum_foundry.provenance import ProvenanceInfo
from quantum_foundry.validation.compute import compute_agreement
from quantum_foundry.validation.schema import (
    BenchmarkEntry,
    Citation,
    ExperimentalValue,
    SimulatedValue,
)

_CITATION = Citation(
    authors="Test et al.", year=2026, title="T", venue="V", doi=None, figure_or_table_ref="Fig. 1"
)


def _entry(exp_value: float, uncertainty: float | None = None) -> BenchmarkEntry:
    exp = ExperimentalValue(
        quantity="mobility", value=exp_value, unit="cm^2/(V*s)", citation=_CITATION, uncertainty=uncertainty
    )
    return BenchmarkEntry(id="test_entry", experimental=exp)


def _sim(value: float, is_stub: bool = True) -> SimulatedValue:
    return SimulatedValue(
        quantity="mobility",
        value=value,
        unit="cm^2/(V*s)",
        provenance=ProvenanceInfo(backend_name="stub", is_stub=is_stub),
    )


def test_not_yet_simulated_when_no_simulated_value():
    result = compute_agreement(_entry(44.0))
    assert result.verdict == "not yet simulated"
    assert result.pct_error is None


def test_exact_match_is_excellent():
    entry = _entry(44.0)
    entry.simulated = _sim(44.0)
    result = compute_agreement(entry)
    assert result.pct_error == 0.0
    assert result.verdict == "excellent"


def test_large_deviation_is_poor():
    entry = _entry(44.0)
    entry.simulated = _sim(88.0)  # 100% error
    result = compute_agreement(entry)
    assert result.pct_error == 100.0
    assert result.verdict == "poor"


def test_moderate_deviation_is_reasonable():
    entry = _entry(100.0)
    entry.simulated = _sim(120.0)  # 20% error
    result = compute_agreement(entry)
    assert result.verdict == "reasonable"


def test_zero_experimental_value_is_handled_explicitly_not_a_crash():
    entry = _entry(0.0)
    entry.simulated = _sim(1.0)
    result = compute_agreement(entry)
    assert result.pct_error is None
    assert "zero" in result.verdict


def test_within_uncertainty_flag():
    entry = _entry(44.0, uncertainty=2.0)
    entry.simulated = _sim(45.5)  # within +/- 2.0 of 44.0
    result = compute_agreement(entry)
    assert result.within_uncertainty is True

    entry2 = _entry(44.0, uncertainty=2.0)
    entry2.simulated = _sim(50.0)  # outside +/- 2.0
    result2 = compute_agreement(entry2)
    assert result2.within_uncertainty is False
