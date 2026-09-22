"""Contract for the device transport stage.

Registered in `transport/__init__.py`'s `get_backend(name, **params)`. See
`docs/ARCHITECTURE.md`'s "The stub/real seam" for the cross-stage pattern.

Today's registered backends: `"stub"` (`transport/stub.py`'s
`LongChannelMOSFETStub` — algebraic long-channel square-law model),
`"kwant"` (`transport/kwant_backend.py` — real atomistic NEGF via Kwant,
discretizes the DFT stage's `TightBindingHandle`), `"devsim"`
(`transport/devsim_backend.py` — semiclassical drift-diffusion; installs
but needs a real BLAS/LAPACK not present in every sandbox, see
`docs/DECISIONS.md`).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..dft.results import DFTResult
from ..materials.schema import MaterialRecord
from .results import DeviceGeometry, TransportResult


@runtime_checkable
class TransportBackend(Protocol):
    """A single device-transport backend (I-V characteristics, mobility).

    Attributes:
        name: Registry key this backend was constructed under.
        is_stub: Whether `run()` is a real solve (`False`) or an
            approximation (`True`); propagated into `TransportResult
            .provenance.is_stub`.
    """

    name: str
    is_stub: bool

    def run(
        self,
        material: MaterialRecord,
        dft_result: DFTResult,
        geometry: DeviceGeometry,
        params: dict,
    ) -> TransportResult:
        """Compute (or approximate) this device's I-V/transport characteristics.

        Args:
            material: The channel's `MaterialRecord` (real, cited fields).
            dft_result: This material's `DFTResult` from the DFT stage —
                real backends (e.g. Kwant) discretize its
                `tight_binding_hamiltonian` handle.
            geometry: `DeviceGeometry` — channel length/width/thickness
                (nm), gate oxide thickness (nm) and material, gate type
                (`"single" | "double" | "gate_all_around"`), and optional
                `stacked_tiers` for CFET/M3D devices (see that field's
                docstring — most backends don't yet consume it beyond
                per-tier orchestration in `orchestration/pipeline.py`).
            params: Backend-specific run parameters, e.g. `"carrier_type"`
                (`"electron" | "hole"`).

        Returns:
            A `TransportResult` (see `transport/results.py`): `ion_uA_per_um`
            /`ioff_uA_per_um` (uA/um), `subthreshold_swing_mV_dec` (mV/dec),
            `mobility_cm2_Vs` (cm^2/V/s), `contact_resistance_ohm_um`
            (ohm*um), `power_density_W_per_um2` (W/um^2), `iv_curve` (list
            of `(V_gs, I_ds)` points), optionally `threshold_voltage_V`/
            `dibl_mV_V` (real backends only — real-curve extraction doesn't
            apply to the stub's algebraic V_t), and a `ProvenanceInfo`
            with `is_stub` set to this backend's own value.
        """
        ...
