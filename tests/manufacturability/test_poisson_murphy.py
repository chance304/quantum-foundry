import pytest

from quantum_foundry.manufacturability.poisson_murphy import (
    MurphyYieldBackend,
    NegativeBinomialYieldBackend,
    PoissonYieldBackend,
    run_murphy,
    run_negative_binomial,
    run_poisson,
)
from quantum_foundry.provenance import ProvenanceInfo
from quantum_foundry.transport.results import DeviceGeometry, TransportResult


def _transport_result() -> TransportResult:
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    return TransportResult(
        device_geometry=geometry, ion_uA_per_um=100.0, ioff_uA_per_um=0.01,
        subthreshold_swing_mV_dec=70.0, mobility_cm2_Vs=30.0, contact_resistance_ohm_um=1000.0,
        power_density_W_per_um2=1e-6, iv_curve=[],
        provenance=ProvenanceInfo(backend_name="test", is_stub=True),
    )


def test_poisson_yield_matches_hand_computed_reference():
    import math

    tr = _transport_result()
    result = run_poisson(tr, defect_density_per_cm2=1000.0, params={"devices_per_die": 1.0})
    area_cm2 = (20.0 * 100.0 * 1e-6) * 1e-8  # matches _critical_area_cm2
    expected = math.exp(-1000.0 * area_cm2)
    assert result.yield_fraction == pytest.approx(expected)
    assert result.model == "poisson"
    assert result.provenance.is_stub is False


def test_murphy_yield_matches_hand_computed_reference():
    import math

    tr = _transport_result()
    result = run_murphy(tr, defect_density_per_cm2=1000.0, params={"devices_per_die": 1.0})
    area_cm2 = (20.0 * 100.0 * 1e-6) * 1e-8
    d0a = 1000.0 * area_cm2
    expected = ((1 - math.exp(-d0a)) / d0a) ** 2
    assert result.yield_fraction == pytest.approx(expected)
    assert result.model == "murphy"


def test_backend_refuses_to_run_without_defect_density():
    tr = _transport_result()
    with pytest.raises(ValueError, match="defect_density_per_cm2"):
        PoissonYieldBackend().run(tr, {})
    with pytest.raises(ValueError, match="defect_density_per_cm2"):
        MurphyYieldBackend().run(tr, {})


def test_backend_runs_with_supplied_defect_density():
    tr = _transport_result()
    result = PoissonYieldBackend().run(tr, {"defect_density_per_cm2": 500.0})
    assert 0.0 <= result.yield_fraction <= 1.0
    assert result.defect_density_per_cm2 == 500.0


def test_negative_binomial_yield_matches_hand_computed_reference():
    tr = _transport_result()
    result = run_negative_binomial(
        tr, defect_density_per_cm2=1000.0, clustering_parameter_alpha=2.0, params={"devices_per_die": 1.0}
    )
    area_cm2 = (20.0 * 100.0 * 1e-6) * 1e-8
    d0a = 1000.0 * area_cm2
    expected = (1 + d0a / 2.0) ** (-2.0)
    assert result.yield_fraction == pytest.approx(expected)
    assert result.model == "negative_binomial"
    assert result.extra["clustering_parameter_alpha"] == 2.0


def test_negative_binomial_converges_to_poisson_as_alpha_grows():
    # As alpha -> infinity, Stapper's negative-binomial model converges to
    # the Poisson result (the uniform-defect-clustering limit) -- a real
    # physics sanity check, not just a golden number.
    tr = _transport_result()
    poisson_result = run_poisson(tr, defect_density_per_cm2=1000.0, params={"devices_per_die": 1.0})
    nb_result = run_negative_binomial(
        tr, defect_density_per_cm2=1000.0, clustering_parameter_alpha=1e6, params={"devices_per_die": 1.0}
    )
    assert nb_result.yield_fraction == pytest.approx(poisson_result.yield_fraction, rel=1e-4)


def test_negative_binomial_backend_refuses_without_alpha():
    tr = _transport_result()
    with pytest.raises(ValueError, match="clustering_parameter_alpha"):
        NegativeBinomialYieldBackend().run(tr, {"defect_density_per_cm2": 500.0})


def test_negative_binomial_backend_refuses_without_defect_density():
    tr = _transport_result()
    with pytest.raises(ValueError, match="defect_density_per_cm2"):
        NegativeBinomialYieldBackend().run(tr, {"clustering_parameter_alpha": 2.0})
