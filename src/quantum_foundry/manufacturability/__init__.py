from __future__ import annotations

from typing import cast

from .interfaces import ManufacturabilityBackend
from .monte_carlo import MonteCarloYieldBackend
from .poisson_murphy import (
    MurphyYieldBackend,
    NegativeBinomialYieldBackend,
    PoissonYieldBackend,
)
from .results import YieldResult
from .stub import TrivialYieldStub


class BackendNotFoundError(KeyError):
    """Raised when get_backend() is asked for an unregistered backend name."""


_BACKENDS = {
    "stub": TrivialYieldStub,
    "poisson": PoissonYieldBackend,
    "murphy": MurphyYieldBackend,
    "negative_binomial": NegativeBinomialYieldBackend,
    "monte_carlo": MonteCarloYieldBackend,
}


def get_backend(name: str, **params) -> ManufacturabilityBackend:
    try:
        cls = _BACKENDS[name]
    except KeyError:
        raise BackendNotFoundError(
            f"No manufacturability backend named {name!r}. Available: {sorted(_BACKENDS)}"
        ) from None
    return cast(ManufacturabilityBackend, cls(**params) if params else cls())


__all__ = [
    "BackendNotFoundError",
    "ManufacturabilityBackend",
    "MonteCarloYieldBackend",
    "MurphyYieldBackend",
    "NegativeBinomialYieldBackend",
    "PoissonYieldBackend",
    "TrivialYieldStub",
    "YieldResult",
    "get_backend",
]
