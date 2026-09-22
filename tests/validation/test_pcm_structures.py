import pytest

from quantum_foundry.validation.pcm_structures import (
    extract_tlm_parameters,
    extract_van_der_pauw_sheet_resistance,
    synthesize_tlm_measurements,
    synthesize_van_der_pauw_measurement,
)


def test_tlm_round_trip_recovers_ground_truth():
    measurements = synthesize_tlm_measurements(
        sheet_resistance_ohm_sq=500.0,
        contact_resistance_ohm_um=800.0,
        channel_width_um=1.0,
        spacings_um=[2.0, 5.0, 10.0, 20.0],
    )
    result = extract_tlm_parameters(measurements, channel_width_um=1.0)
    assert result.sheet_resistance_ohm_sq == pytest.approx(500.0, rel=1e-6)
    assert result.contact_resistance_ohm_um == pytest.approx(800.0, rel=1e-6)


def test_tlm_requires_at_least_two_spacings():
    with pytest.raises(ValueError, match="at least 2"):
        extract_tlm_parameters([(5.0, 100.0)], channel_width_um=1.0)


def test_tlm_rejects_negative_intercept_as_invalid():
    # Two points implying a negative contact-resistance intercept -- not a
    # real physical result, must be refused rather than returned.
    with pytest.raises(ValueError, match="negative contact-resistance"):
        extract_tlm_parameters([(1.0, 1.0), (2.0, 3.0)], channel_width_um=1.0)


def test_van_der_pauw_round_trip_symmetric_case_matches_simplified_formula():
    # At perfect symmetry (Ra == Rb), the real transcendental solve must
    # agree with the well-known simplified formula Rs = (pi/ln2)*Ra.
    r_a, r_b = synthesize_van_der_pauw_measurement(sheet_resistance_ohm_sq=300.0, asymmetry_ratio=1.0)
    assert r_a == pytest.approx(r_b, rel=1e-9)
    extracted = extract_van_der_pauw_sheet_resistance(r_a, r_b)
    assert extracted == pytest.approx(300.0, rel=1e-6)


def test_van_der_pauw_round_trip_asymmetric_case():
    # Proves the real transcendental equation is being solved, not the
    # simplified symmetric-sample shortcut -- Ra != Rb here.
    r_a, r_b = synthesize_van_der_pauw_measurement(sheet_resistance_ohm_sq=300.0, asymmetry_ratio=1.4)
    assert r_a != pytest.approx(r_b)
    extracted = extract_van_der_pauw_sheet_resistance(r_a, r_b)
    assert extracted == pytest.approx(300.0, rel=1e-6)


def test_van_der_pauw_rejects_nonpositive_inputs():
    with pytest.raises(ValueError, match="positive"):
        extract_van_der_pauw_sheet_resistance(0.0, 100.0)
    with pytest.raises(ValueError, match="positive"):
        synthesize_van_der_pauw_measurement(300.0, asymmetry_ratio=0.0)
