from __future__ import annotations

from typing import cast

from .hotspot_backend import HotSpotThermalBackend
from .interfaces import ThermalBackend
from .results import FieldHandle, MaterialStack, ThermalLayer, ThermalResult
from .stub import LumpedRCThermalStub, default_stack_from_geometry

# Real 3D FEA backends (fenicsx_backend.py, elmer_backend.py) are M5 —
# planning only so far, see docs/M5_PLAN.md.


class BackendNotFoundError(KeyError):
    """Raised when get_backend() is asked for an unregistered backend name."""


_BACKENDS = {
    "stub": LumpedRCThermalStub,
    "hotspot": HotSpotThermalBackend,
}


def get_backend(name: str, **params) -> ThermalBackend:
    try:
        cls = _BACKENDS[name]
    except KeyError:
        raise BackendNotFoundError(
            f"No thermal backend named {name!r}. Available: {sorted(_BACKENDS)}"
        ) from None
    return cast(ThermalBackend, cls(**params) if params else cls())


__all__ = [
    "BackendNotFoundError",
    "FieldHandle",
    "HotSpotThermalBackend",
    "LumpedRCThermalStub",
    "MaterialStack",
    "ThermalBackend",
    "ThermalLayer",
    "ThermalResult",
    "default_stack_from_geometry",
    "get_backend",
]
