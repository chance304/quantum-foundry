from __future__ import annotations

from typing import cast

from .devsim_backend import DEVSIMTransportBackend
from .interfaces import TransportBackend
from .kwant_backend import KwantTransportBackend
from .results import DeviceGeometry, TransportResult
from .stub import LongChannelMOSFETStub


class BackendNotFoundError(KeyError):
    """Raised when get_backend() is asked for an unregistered backend name."""


_BACKENDS = {
    "stub": LongChannelMOSFETStub,
    "devsim": DEVSIMTransportBackend,
    "kwant": KwantTransportBackend,
}


def get_backend(name: str, **params) -> TransportBackend:
    try:
        cls = _BACKENDS[name]
    except KeyError:
        raise BackendNotFoundError(
            f"No transport backend named {name!r}. Available: {sorted(_BACKENDS)}"
        ) from None
    return cast(TransportBackend, cls(**params) if params else cls())


__all__ = [
    "BackendNotFoundError",
    "DEVSIMTransportBackend",
    "DeviceGeometry",
    "KwantTransportBackend",
    "LongChannelMOSFETStub",
    "TransportBackend",
    "TransportResult",
    "get_backend",
]
