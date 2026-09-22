from quantum_foundry.manufacturability.functional_criteria import (
    FUNCTIONAL_ION_IOFF_RATIO_MIN,
    is_functional_transistor,
)


def test_functional_when_ratio_exceeds_threshold():
    assert is_functional_transistor(ion_uA_per_um=100.0, ioff_uA_per_um=100.0 / 1e6) is True


def test_not_functional_when_ratio_below_threshold():
    assert is_functional_transistor(ion_uA_per_um=100.0, ioff_uA_per_um=100.0 / 1e3) is False


def test_exactly_at_threshold_passes():
    ion = 100.0
    ioff = ion / FUNCTIONAL_ION_IOFF_RATIO_MIN
    assert is_functional_transistor(ion, ioff) is True


def test_zero_ioff_is_trivially_functional():
    assert is_functional_transistor(ion_uA_per_um=100.0, ioff_uA_per_um=0.0) is True


def test_custom_ratio_threshold():
    assert is_functional_transistor(ion_uA_per_um=100.0, ioff_uA_per_um=1.0, min_ratio=10.0) is True
    assert is_functional_transistor(ion_uA_per_um=100.0, ioff_uA_per_um=1.0, min_ratio=1000.0) is False
