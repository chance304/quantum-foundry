import pytest

from quantum_foundry.manufacturability import BackendNotFoundError, get_backend


def test_get_backend_stub():
    backend = get_backend("stub")
    assert backend.is_stub is True


def test_get_backend_poisson_and_murphy():
    assert get_backend("poisson").is_stub is False
    assert get_backend("murphy").is_stub is False


def test_get_backend_negative_binomial():
    assert get_backend("negative_binomial").is_stub is False


def test_get_backend_monte_carlo():
    assert get_backend("monte_carlo").is_stub is False


def test_get_backend_unknown_raises_with_available_list():
    with pytest.raises(BackendNotFoundError, match="stub"):
        get_backend("nonexistent")
