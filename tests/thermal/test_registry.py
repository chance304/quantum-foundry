import pytest

from quantum_foundry.thermal import BackendNotFoundError, get_backend


def test_get_backend_stub():
    backend = get_backend("stub")
    assert backend.name == "stub"
    assert backend.is_stub is True


def test_get_backend_hotspot_importable_without_binary_present():
    backend = get_backend("hotspot")
    assert backend.is_stub is False


def test_get_backend_unknown_raises_with_available_list():
    with pytest.raises(BackendNotFoundError, match="stub"):
        get_backend("nonexistent")
