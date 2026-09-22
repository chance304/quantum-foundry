"""Contract for the manufacturability/yield stage.

Registered in `manufacturability/__init__.py`'s `get_backend(name, **params)`.
See `docs/ARCHITECTURE.md`'s "The stub/real seam" for the cross-stage
pattern.

Today's registered backends span a wider real-vs-stub range than the other
stages: `poisson_murphy.py`'s `PoissonYieldBackend`/`MurphyYieldBackend`/
`NegativeBinomialYieldBackend` are real, closed-form models (no mature
open-source package exists for this layer — foundries build it in-house
too, see `CLAUDE.md`), and `monte_carlo.py` is a real defect-placement
Monte Carlo. `stub.py` is the cheap linear approximation. Every non-stub
model here still refuses to fabricate its own inputs (e.g. defect density
D0, clustering parameter alpha) without a real, cited source or an
explicit caller-supplied value — see `manufacturability/stub.py`'s
`extra["defect_density_defaulted_uncited"]` flag for how an unavoidable
placeholder is surfaced rather than hidden.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..transport.results import TransportResult
from .results import YieldResult


@runtime_checkable
class ManufacturabilityBackend(Protocol):
    """A single yield/manufacturability backend.

    Attributes:
        name: Registry key this backend was constructed under.
        is_stub: Whether `run()` is a real model (`False`) or a cheap
            approximation (`True`); propagated into `YieldResult
            .provenance.is_stub`.
    """

    name: str
    is_stub: bool

    def run(self, transport_result: TransportResult, params: dict) -> YieldResult:
        """Compute (or approximate) this device's manufacturing yield.

        Args:
            transport_result: The upstream `TransportResult` — device
                geometry (via `transport_result.device_geometry`) feeds the
                critical-area estimate most yield models need.
            params: Backend-specific run parameters, e.g. defect density
                (`per cm^2`) and clustering parameter, when the backend
                requires them explicitly rather than defaulting silently.

        Returns:
            A `YieldResult` (see `manufacturability/results.py`):
            `yield_fraction` (0-1), `defect_density_per_cm2`,
            `critical_area_um2` (um^2, `None` if not computed),
            `model` (`"trivial_linear" | "poisson" | "murphy" |
            "negative_binomial" | "monte_carlo"`), an optional
            `confidence_interval` tuple, and a `ProvenanceInfo` with
            `is_stub` set to this backend's own value.
        """
        ...
