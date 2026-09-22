import pytest

from quantum_foundry.transport.extraction import (
    compute_dibl_mV_per_V,
    extract_vth_constant_current,
)


def test_extract_vth_constant_current_interpolates_in_log_space():
    # Exponential subthreshold current: exactly 1e-7 A/um (=0.1 uA/um) at
    # vgs=0.3, so the criterion crossing should land almost exactly there.
    vgs_sweep = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    currents_uA_per_um = [1e-5, 1e-4, 1e-3, 1e-1, 1e1, 1e3]
    vth = extract_vth_constant_current(vgs_sweep, currents_uA_per_um)
    assert vth == pytest.approx(0.3, abs=0.02)


def test_extract_vth_constant_current_raises_when_never_crossed():
    vgs_sweep = [0.0, 0.1, 0.2]
    currents_uA_per_um = [1e-9, 1e-8, 1e-7]  # never reaches 0.1 uA/um
    with pytest.raises(ValueError, match="never crosses"):
        extract_vth_constant_current(vgs_sweep, currents_uA_per_um)


def test_extract_vth_constant_current_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="same length"):
        extract_vth_constant_current([0.0, 0.1], [1.0])


def test_dibl_positive_when_vth_rolls_off_at_higher_vds():
    # Vth drops from 0.30V (low Vds) to 0.25V (high Vds) over a 0.75V swing
    # -> DIBL = -(0.25-0.30)/(0.8-0.05)*1000 = 66.67 mV/V, the expected
    # short-channel-effect direction (positive).
    dibl = compute_dibl_mV_per_V(vth_low_vds_V=0.30, vth_high_vds_V=0.25, vds_low_V=0.05, vds_high_V=0.80)
    assert dibl == pytest.approx(66.67, abs=0.1)


def test_dibl_zero_when_vth_unchanged():
    dibl = compute_dibl_mV_per_V(vth_low_vds_V=0.30, vth_high_vds_V=0.30, vds_low_V=0.05, vds_high_V=0.80)
    assert dibl == pytest.approx(0.0)


def test_dibl_rejects_equal_vds_points():
    with pytest.raises(ValueError, match="differ"):
        compute_dibl_mV_per_V(0.3, 0.25, 0.5, 0.5)
