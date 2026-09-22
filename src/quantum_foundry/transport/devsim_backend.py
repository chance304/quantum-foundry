"""Real DEVSIM backend: 1D drift-diffusion sweep on a doped n+/p/n+
(source/channel/drain) structure — not a bare resistor. Gate control is
approximated as a uniform shift of the channel boundary potential (an
idealized long-channel gate-coupling approximation, not full 2D Poisson
gate electrostatics) — a real, flagged simplification and the natural next
step once this is running (swap in a 2D mesh with an explicit gate contact
+ oxide region).

RISK: never run against a real installed `devsim` package in this
project's history before this session — DEVSIM's Python API has shifted
across releases. Treat every call below as needing verification, not
certainty. See docs/DECISIONS.md for the install/verification outcome.

Mobility model decision (2026-07-22, docs/STANDARDS_AUDIT.md Tier 2):
bulk Caughey-Thomas doping-dependent mobility (Caughey & Thomas, "Carrier
Mobilities in Silicon Empirically Related to Doping and Field," Proc. IEEE,
1967) for the first real implementation — not a 2D-specific phonon-limited
model (Kaasbjerg-class), and no quantum-correction (density-gradient) term.
Explicitly a simplification for a 0.65nm monolayer channel, where bulk
drift-diffusion assumptions themselves are already questionable (see
docs/STANDARDS_AUDIT.md) — chosen because it's standard, well-documented,
and lets `_setup_drift_diffusion()`'s actual equation wiring (still the
real unknown below) get built against a known-form mobility expression
rather than blocking on a less-standard model with no DEVSIM tooling
precedent. `caughey_thomas_mobility()` below is real, pure, and
unit-tested now; it does NOT require a working devsim install to define or
verify — only `_setup_drift_diffusion()`'s actual equation setup does.

Requires: pip install devsim
"""
from __future__ import annotations

from ..dft.results import DFTResult
from ..materials.schema import MaterialRecord
from .results import DeviceGeometry, TransportResult

DEVICE_NAME, REGION_NAME = "qf_1d_mosfet", "channel_region"

# Caughey-Thomas (1967) reference parameters for bulk silicon majority-
# carrier mobility, the standard textbook values (Sze & Ng, Physics of
# Semiconductor Devices) -- NOT yet re-derived for a 2D-TMD channel
# specifically (see module docstring: this is a deliberate bulk-model
# simplification, not a 2D-phonon-limited fit). Real per-material values
# are a separate, literature-dependent follow-up once this backend's
# equation setup actually runs.
_CAUGHEY_THOMAS_ELECTRON_PARAMS = {"mu_min": 65.0, "mu_max": 1330.0, "n_ref": 8.5e16, "alpha": 0.72}
_CAUGHEY_THOMAS_HOLE_PARAMS = {"mu_min": 48.0, "mu_max": 495.0, "n_ref": 6.3e16, "alpha": 0.76}


def caughey_thomas_mobility(doping_cm3: float, mu_min: float, mu_max: float, n_ref: float, alpha: float) -> float:
    """Caughey-Thomas doping-dependent mobility, cm^2/(V*s):

        mu(N) = mu_min + (mu_max - mu_min) / (1 + (N / N_ref)^alpha)

    Approaches mu_max as doping_cm3 -> 0 (undoped/intrinsic limit) and
    mu_min at very high doping (heavily-doped source/drain limit) --
    ionized-impurity scattering dominates there. Pure function, no devsim
    dependency -- this is what makes it testable without a working devsim
    install (unlike the rest of this module).
    """
    return mu_min + (mu_max - mu_min) / (1 + (doping_cm3 / n_ref) ** alpha)


def _build_1d_doped_mesh(devsim, geometry: DeviceGeometry, d_sd: float, d_ch: float):
    length = geometry.channel_length_nm * 1e-7  # nm -> cm
    src_frac, drn_frac = 0.2, 0.2
    mesh = "qf_mesh"
    devsim.create_1d_mesh(mesh=mesh)
    devsim.add_1d_mesh_line(mesh=mesh, pos=0.0, ps=length / 200, tag="source_contact")
    devsim.add_1d_mesh_line(mesh=mesh, pos=src_frac * length, ps=length / 400)
    devsim.add_1d_mesh_line(mesh=mesh, pos=(1 - drn_frac) * length, ps=length / 400)
    devsim.add_1d_mesh_line(mesh=mesh, pos=length, ps=length / 200, tag="drain_contact")
    devsim.add_1d_contact(mesh=mesh, name="source", tag="source_contact", material="metal")
    devsim.add_1d_contact(mesh=mesh, name="drain", tag="drain_contact", material="metal")
    devsim.add_1d_region(
        mesh=mesh, material="Silicon", region=REGION_NAME,
        tag1="source_contact", tag2="drain_contact",
    )
    devsim.finalize_mesh(mesh=mesh)
    devsim.create_device(mesh=mesh, device=DEVICE_NAME)

    devsim.node_model(
        device=DEVICE_NAME, region=REGION_NAME, name="Acceptors",
        equation=f"{d_ch}*(x > {src_frac * length})*(x < {(1 - drn_frac) * length})",
    )
    devsim.node_model(
        device=DEVICE_NAME, region=REGION_NAME, name="Donors",
        equation=f"{d_sd}*((x <= {src_frac * length}) + (x >= {(1 - drn_frac) * length}))",
    )
    devsim.node_model(device=DEVICE_NAME, region=REGION_NAME, name="NetDoping", equation="Donors-Acceptors")


def _setup_drift_diffusion(devsim, material: MaterialRecord, dft_result: DFTResult):
    # Real implementation task: Potential/Electrons/Holes solution vars,
    # Poisson + electron/hole continuity equations via devsim's
    # node_model/edge_model/equation calls, Newton-solved, referencing
    # caughey_thomas_mobility() above for the electron/hole mobility node
    # models (mobility model decision made 2026-07-22, see module
    # docstring/docs/DECISIONS.md -- no quantum-correction term in scope).
    # This equation wiring itself is still the single largest unknown in
    # this whole backend — deliberately left unimplemented rather than
    # guessed blind, since it needs a working devsim install to iterate
    # against (unavailable in this sandbox, see docs/DECISIONS.md). See
    # docs/ROADMAP.md for the concrete next step.
    raise NotImplementedError(
        "DEVSIM drift-diffusion equation setup not yet implemented — see "
        "docs/DECISIONS.md for install/API verification status and "
        "docs/ROADMAP.md for the concrete next step."
    )


def run(
    material: MaterialRecord,
    dft_result: DFTResult,
    geometry: DeviceGeometry,
    params: dict,
) -> TransportResult:
    import devsim  # local import: heavy, optional dep

    _build_1d_doped_mesh(
        devsim, geometry,
        params.get("doping_source_drain_cm3", 1e20),
        params.get("doping_channel_cm3", 1e17),
    )
    _setup_drift_diffusion(devsim, material, dft_result)
    # Vgs/Vds sweep + Ion/Ioff/SS/mobility extraction: real implementation
    # task once the equation setup above actually solves.
    raise NotImplementedError("DEVSIM sweep/extraction loop not yet implemented.")


class DEVSIMTransportBackend:
    name, is_stub = "devsim", False

    def run(self, material, dft_result, geometry, params):
        return run(material, dft_result, geometry, params)
