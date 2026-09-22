from quantum_foundry.provenance import ProvenanceInfo
from quantum_foundry.validation.registry import BenchmarkRegistry
from quantum_foundry.validation.report import render_markdown
from quantum_foundry.validation.schema import SimulatedValue


def test_loads_real_seeded_benchmarks():
    registry = BenchmarkRegistry()
    ids = {entry.id for entry in registry.all_entries()}
    assert ids == {
        "mos2_rc_ni_uhv",
        "mos2_rc_edge_contact_record",
        "mos2_ion_edge_contact_120nm",
        "mos2_mobility_bare_sio2",
        "mos2_mobility_optimized",
        "mos2_subthreshold_swing",
    }


def test_report_renders_cleanly_with_no_simulated_values_yet():
    registry = BenchmarkRegistry()
    report = render_markdown(registry)
    assert "# Validation Report" in report
    assert "not yet simulated" in report
    assert "mos2_rc_ni_uhv" not in report  # id isn't in the table, quantity name is
    assert "contact_resistance" in report


def test_report_shows_pct_error_and_stub_flag_once_simulated():
    registry = BenchmarkRegistry()
    simulated = SimulatedValue(
        quantity="mobility",
        value=46.0,
        unit="cm^2/(V*s)",
        provenance=ProvenanceInfo(backend_name="stub", is_stub=True),
        conditions={"material": "MoS2_monolayer", "substrate": "SiO2", "high_k_dielectric": False},
    )
    matched = registry.attach_simulated(simulated)
    assert len(matched) == 1
    assert matched[0].id == "mos2_mobility_bare_sio2"

    report = render_markdown(registry)
    assert "(stub)" in report
    assert "%" in report


def test_conditions_disambiguate_two_contact_resistance_benchmarks():
    """The two Rc benchmarks (UHV Ni vs. edge-contact) must not be conflated."""
    registry = BenchmarkRegistry()
    simulated = SimulatedValue(
        quantity="contact_resistance",
        value=1300.0,
        unit="ohm*um",
        provenance=ProvenanceInfo(backend_name="stub", is_stub=True),
        conditions={"material": "MoS2_monolayer", "contact_type": "edge"},
    )
    matched = registry.attach_simulated(simulated)
    assert len(matched) == 1
    assert matched[0].id == "mos2_rc_edge_contact_record"
    assert registry.get("mos2_rc_ni_uhv").simulated is None
