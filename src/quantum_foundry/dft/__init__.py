from __future__ import annotations

from .interfaces import DFTBackend
from .results import DFTResult, TightBindingHandle
from .stub import EffectiveMassDFTStub

# Real backend (qe_wannier.py) deferred to M5 — not built yet.


class BackendNotFoundError(KeyError):
    """Raised when get_backend() is asked for an unregistered backend name."""


_BACKENDS = {
    "stub": EffectiveMassDFTStub,
}


def get_backend(name: str, **params) -> DFTBackend:
    try:
        cls = _BACKENDS[name]
    except KeyError:
        raise BackendNotFoundError(
            f"No DFT backend named {name!r}. Available: {sorted(_BACKENDS)}"
        ) from None
    return cls(**params) if params else cls()


__all__ = [
    "BackendNotFoundError",
    "DFTBackend",
    "DFTResult",
    "EffectiveMassDFTStub",
    "TightBindingHandle",
    "get_backend",
]
