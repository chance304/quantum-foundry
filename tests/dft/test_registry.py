import pytest

from quantum_foundry.dft import BackendNotFoundError, get_backend


def test_get_backend_stub():
    backend = get_backend("stub")
    assert backend.name == "stub"
    assert backend.is_stub is True


def test_get_backend_unknown_raises_with_available_list():
    with pytest.raises(BackendNotFoundError, match="stub"):
        get_backend("nonexistent")
