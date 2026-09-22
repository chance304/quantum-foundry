"""Contract for the ab-initio (DFT) stage.

Any class satisfying this Protocol is registered in `dft/__init__.py`'s
`get_backend(name, **params)` and is interchangeable with any other —
`orchestration/pipeline.py` only ever calls this interface, never a
concrete backend class. See `docs/ARCHITECTURE.md`'s "The stub/real seam"
for the cross-stage pattern this belongs to.

Today's registered backends: `"stub"` (`dft/stub.py`'s
`EffectiveMassDFTStub` — real, cited `MaterialRecord` fields fed through a
single-band parabolic model, no ab-initio solve). A real Quantum
ESPRESSO + Wannier90 backend is deferred to M5 (`docs/M5_PLAN.md`) and not
yet registered.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..materials.schema import MaterialRecord
from .results import DFTResult


@runtime_checkable
class DFTBackend(Protocol):
    """A single ab-initio/effective-band-structure backend.

    Attributes:
        name: The registry key this backend was constructed under (matches
            the key in `dft/__init__.py`'s `_BACKENDS`).
        is_stub: Whether `run()` performs a real ab-initio solve (`False`)
            or an approximation (`True`). Propagated into every
            `DFTResult.provenance.is_stub` this backend produces — the
            mechanism the rest of the pipeline (and every validation
            report) uses to tell a real number from a stand-in.
    """

    name: str
    is_stub: bool

    def run(self, material: MaterialRecord, params: dict) -> DFTResult:
        """Compute (or approximate) this material's electronic structure.

        Args:
            material: A `MaterialRecord` from `materials/registry.py`,
                already carrying real, cited fields (band gap in eV,
                effective masses in units of the free-electron mass m0,
                lattice constant in angstrom).
            params: Backend-specific run parameters. The one contract-wide
                key today is `"carrier_type"` (`"electron" | "hole" |`
                omitted) — see `dft/stub.py`'s module docstring for how
                the stub backend uses it to decide which effective mass is
                actually required.

        Returns:
            A `DFTResult` (see `dft/results.py`) carrying the resolved
            band gap (eV), effective mass(es) (m0, may be `None` if the
            requested carrier role's mass wasn't required), lattice
            constant (angstrom), a `TightBindingHandle` usable by a real
            transport backend (e.g. `transport/kwant_backend.py`'s
            `kwant.continuum.discretize`), and a `ProvenanceInfo` with
            `is_stub` set to this backend's own value.
        """
        ...
