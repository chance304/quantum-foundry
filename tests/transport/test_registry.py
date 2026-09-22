import pytest

from quantum_foundry.transport import BackendNotFoundError, get_backend


def test_get_backend_stub():
    backend = get_backend("stub")
    assert backend.name == "stub"
    assert backend.is_stub is True


def test_get_backend_devsim_and_kwant_importable_without_packages_installed():
    """The registry must be importable and constructible even if devsim/kwant
    aren't installed — heavy imports are deferred into .run(), not module
    top-level (see docs/DECISIONS.md's repo-wide rule)."""
    devsim_backend = get_backend("devsim")
    kwant_backend = get_backend("kwant")
    assert devsim_backend.is_stub is False
    assert kwant_backend.is_stub is False


def test_get_backend_unknown_raises_with_available_list():
    with pytest.raises(BackendNotFoundError, match="stub"):
        get_backend("nonexistent")
