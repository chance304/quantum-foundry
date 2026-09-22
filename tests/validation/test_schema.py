from quantum_foundry.provenance import ProvenanceInfo
from quantum_foundry.validation.schema import (
    BenchmarkEntry,
    Citation,
    ExperimentalValue,
    SimulatedValue,
)


def test_experimental_value_requires_citation():
    citation = Citation(
        authors="Test et al.",
        year=2026,
        title="Test paper",
        venue="Test Venue",
        doi=None,
        figure_or_table_ref="Fig. 1",
    )
    exp = ExperimentalValue(quantity="contact_resistance", value=500.0, unit="ohm*um", citation=citation)
    assert exp.citation.figure_or_table_ref == "Fig. 1"


def test_benchmark_entry_starts_with_no_simulated_value():
    citation = Citation(
        authors="Test et al.", year=2026, title="T", venue="V", doi=None, figure_or_table_ref="Fig. 1"
    )
    exp = ExperimentalValue(quantity="mobility", value=44.0, unit="cm^2/(V*s)", citation=citation)
    entry = BenchmarkEntry(id="test_entry", experimental=exp)
    assert entry.simulated is None


def test_simulated_value_uncertainty_defaults_to_none():
    sim = SimulatedValue(
        quantity="mobility",
        value=30.0,
        unit="cm^2/(V*s)",
        provenance=ProvenanceInfo(backend_name="test", is_stub=True),
    )
    assert sim.uncertainty is None


def test_simulated_value_uncertainty_is_settable():
    sim = SimulatedValue(
        quantity="mobility",
        value=30.0,
        unit="cm^2/(V*s)",
        provenance=ProvenanceInfo(backend_name="test", is_stub=False),
        uncertainty=1.5,
    )
    assert sim.uncertainty == 1.5
