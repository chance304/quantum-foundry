import pytest

from quantum_foundry.transport.mobility_degradation import (
    defect_limited_mobility,
    matthiessens_rule_mobility,
)


def test_matthiessens_rule_combines_reciprocals():
    # 1/mu = 1/100 + 1/100 -> mu = 50
    assert matthiessens_rule_mobility(100.0, 100.0) == pytest.approx(50.0)


def test_matthiessens_rule_dominated_by_smaller_mobility():
    mu = matthiessens_rule_mobility(1000.0, 10.0)
    assert mu < 10.0  # combined mobility is always less than either component


def test_matthiessens_rule_rejects_nonpositive_inputs():
    with pytest.raises(ValueError, match="positive"):
        matthiessens_rule_mobility(0.0, 100.0)
    with pytest.raises(ValueError, match="positive"):
        matthiessens_rule_mobility(100.0, -1.0)


def test_defect_limited_mobility_inverse_relationship():
    mu_low_defect = defect_limited_mobility(defect_density_per_cm2=1e10, scattering_coefficient_per_Vs=1e15)
    mu_high_defect = defect_limited_mobility(defect_density_per_cm2=1e12, scattering_coefficient_per_Vs=1e15)
    assert mu_high_defect < mu_low_defect


def test_defect_limited_mobility_infinite_at_zero_defects():
    assert defect_limited_mobility(defect_density_per_cm2=0.0, scattering_coefficient_per_Vs=1e15) == float("inf")


def test_defect_limited_mobility_rejects_bad_inputs():
    with pytest.raises(ValueError, match="non-negative"):
        defect_limited_mobility(defect_density_per_cm2=-1.0, scattering_coefficient_per_Vs=1e15)
    with pytest.raises(ValueError, match="positive"):
        defect_limited_mobility(defect_density_per_cm2=1e10, scattering_coefficient_per_Vs=0.0)
