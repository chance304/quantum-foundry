import math

import pytest

from quantum_foundry.manufacturability.monte_carlo import (
    MonteCarloYieldBackend,
    dies_per_wafer,
    run_monte_carlo,
)
from quantum_foundry.manufacturability.poisson_murphy import run_poisson
from quantum_foundry.provenance import ProvenanceInfo
from quantum_foundry.transport.results import DeviceGeometry, TransportResult


def _transport_result(ion=100.0, ioff=0.001) -> TransportResult:
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    return TransportResult(
        device_geometry=geometry, ion_uA_per_um=ion, ioff_uA_per_um=ioff,
        subthreshold_swing_mV_dec=70.0, mobility_cm2_Vs=30.0, contact_resistance_ohm_um=1000.0,
        power_density_W_per_um2=1e-6, iv_curve=[],
        provenance=ProvenanceInfo(backend_name="test", is_stub=True),
    )


def test_dies_per_wafer_reasonable_for_a_realistic_die_size():
    # A ~1cm^2 die on a 300mm wafer should yield on the order of a few
    # hundred to a thousand gross dies -- a real sanity range, not a
    # specific golden number (this is an approximation, see module docstring).
    n = dies_per_wafer(die_area_cm2=1.0)
    assert 400 < n < 700


def test_dies_per_wafer_zero_for_nonpositive_area():
    assert dies_per_wafer(die_area_cm2=0.0) == 0
    assert dies_per_wafer(die_area_cm2=-1.0) == 0


def test_monte_carlo_converges_to_closed_form_poisson_as_n_grows():
    # Poisson is the analytic large-N limit of this same spatial process --
    # verifies the Monte Carlo engine's numerical convergence, exactly what
    # one of the team's supplementary audit prompts asked to check.
    tr = _transport_result()
    poisson_result = run_poisson(tr, defect_density_per_cm2=50.0, params={"devices_per_die": 1.0})
    mc_result = run_monte_carlo(
        tr, defect_density_per_cm2=50.0,
        params={"devices_per_die": 1.0, "n_runs": 20000, "dies_per_wafer": 5000, "rng_seed": 42},
    )
    assert mc_result.yield_fraction == pytest.approx(poisson_result.yield_fraction, abs=0.02)


def test_monte_carlo_populates_confidence_interval():
    # First real backend to ever populate this schema field (always None
    # from every closed-form model, since those aren't stochastic).
    tr = _transport_result()
    result = run_monte_carlo(tr, defect_density_per_cm2=50.0, params={"n_runs": 500, "rng_seed": 1})
    assert result.confidence_interval is not None
    lo, hi = result.confidence_interval
    assert 0.0 <= lo <= result.yield_fraction <= hi <= 1.0


def test_monte_carlo_zeroes_yield_when_ion_ioff_gate_fails():
    tr = _transport_result(ion=100.0, ioff=100.0)  # ratio 1.0, far below 1e5
    result = run_monte_carlo(tr, defect_density_per_cm2=1.0, params={"n_runs": 200, "rng_seed": 2})
    assert result.yield_fraction == 0.0
    assert result.extra["ion_ioff_functional_gate_passed"] is False


def test_backend_requires_defect_density():
    tr = _transport_result()
    with pytest.raises(ValueError, match="defect_density_per_cm2"):
        MonteCarloYieldBackend().run(tr, {})


def test_backend_runs_with_supplied_defect_density():
    tr = _transport_result()
    result = MonteCarloYieldBackend().run(tr, {"defect_density_per_cm2": 10.0, "n_runs": 300, "rng_seed": 3})
    assert 0.0 <= result.yield_fraction <= 1.0
    assert result.model == "monte_carlo"
    assert math.isfinite(result.yield_fraction)
