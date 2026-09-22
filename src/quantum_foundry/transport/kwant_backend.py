"""Real Kwant NEGF backend: discretizes the DFT stub's continuum
effective-mass Hamiltonian into a finite-difference tight-binding lattice
(kwant.continuum.discretize) and computes 2-terminal conductance/current via
Landauer-Buttiker transmission — a genuine quantum-transport calculation on
a channel-appropriate model, not an arbitrary chain.

VERIFIED 2026-07-21 against a real installed kwant 1.5.0 (built from source
in this session — see docs/DECISIONS.md for the install story). The first
version of this module used an API that doesn't exist in kwant 1.5
(`syst[template.shape(...)] = onsite`) — the real API is
`syst.fill(template, shape_fn, start)`, with the discretized template's own
onsite/hopping functions consuming symbolic parameters (here: V, hbar, m_e)
passed via `params=` at kwant.smatrix() call time, not overridden per-site.
Fixed and re-verified end-to-end against the real package, not guessed.

Requires: pip install kwant (or conda-forge kwant). This session's install
needed a from-source Cython rebuild (kwant's published wheel/sdist ships a
pre-generated C file incompatible with NumPy 2.x's C API) plus tinyarray and
sympy as runtime deps — see docs/DECISIONS.md.

Contact/lead model (flagged 2026-07-21 standards audit, docs/STANDARDS_AUDIT.md):
the leads built in _build_system() below are literal semi-infinite periodic
copies of the channel lattice itself (kwant.TranslationalSymmetry over the
same template) -- effectively an idealized, wide-band-limit-equivalent
contact, not a real metal/2D-material contact's own self-consistent self-
energy. This is a legitimate Phase-1 simplification (same-material contacts
are a standard first NEGF approximation, per Datta's own textbook treatment)
but a real one, not yet a deliberate physics choice documented anywhere else
in this codebase -- see extra["contact_model"] on every TransportResult this
backend produces.

M9c (2026-07-27, docs/M9_PLAN.md) -- CFET via decoupled per-tier runs:
`orchestration/pipeline.py`'s M9a already runs this backend once per
DeviceTier when DeviceGeometry.stacked_tiers is set (each tier's own
material/carrier_type/derived single-tier geometry) -- no new code was
needed here for that, since this module already only ever modeled one
planar channel per call. Genuinely verified working for two independent
tiers (tests/e2e/test_real_pipeline.py::test_kwant_backend_cfet_two_tiers_real_run).
This is the "decoupled approximation" M9_PLAN.md recommended -- real inter-
tier/shared-gate electrostatic coupling is not modeled (flagged explicitly
below), same honesty class as the same-material-contact simplification above.

GAA (gate-all-around), deliberately NOT modeled as different physics here:
a real wrap-around gate's stronger electrostatic control needs either a
cited body-factor/subthreshold-swing-degradation parameter or true 3D
confinement -- neither exists yet, and inventing an uncited "gate coupling
strength" multiplier would violate this project's own never-fabricate-a-
constant discipline (docs/STANDARDS_AUDIT.md). `run()` below reads
geometry.gate_type and flags it honestly in extra
(gate_type_requested/gate_type_physics_modeled) instead -- every gate_type
today gets the identical single-gate potential model, and that's stated
plainly rather than silently implied to be geometry-aware.
"""
from __future__ import annotations

import math

from ..dft.results import DFTResult
from ..provenance import ProvenanceInfo
from .extraction import compute_dibl_mV_per_V, extract_vth_constant_current
from .results import DeviceGeometry, TransportResult

_LANDAUER_QUANTUM = 7.748e-5  # 2e^2/h, siemens

# Real, measured constraint (found 2026-07-21 running against the actual
# installed kwant 1.5.0, no MUMPS available -- SciPy's dense fallback
# solver is the bottleneck): a naive lattice_spacing = channel_length/200
# combined with a full device channel_width_nm (e.g. 100nm) produces a
# ~200,000-site lattice and kwant.smatrix() effectively hangs. This is a
# real Phase-1 scope limit, not a bug to silently paper over -- capped
# explicitly below rather than left to hang.
_MAX_TRACTABLE_SITES = 4000


class LatticeTooLargeError(ValueError):
    """Raised when the requested geometry/grid would produce a lattice too
    large for kwant's SciPy dense fallback solver (no MUMPS in this
    environment) to solve in reasonable time. Narrow the device_geometry
    (channel_width_nm in particular) or coarsen lattice_spacing_nm."""


def _in_barrier_region(x: float, geometry: DeviceGeometry) -> bool:
    length = geometry.channel_length_nm
    return 0.2 * length <= x <= 0.8 * length  # matches devsim_backend.py's src/channel/drain split


def _make_potential(band_gap_eV: float, vgs: float, geometry: DeviceGeometry):
    def potential(x, y):
        barrier = band_gap_eV if _in_barrier_region(x, geometry) else 0.0
        return barrier - vgs

    return potential


def _build_system(kwant, template, geometry: DeviceGeometry, lattice_spacing: float):
    def shape(site):
        x, y = site.pos
        return 0 <= x < geometry.channel_length_nm and 0 <= y < geometry.channel_width_nm

    def lead_shape(site):
        _, y = site.pos
        return 0 <= y < geometry.channel_width_nm

    syst = kwant.Builder()
    syst.fill(template, shape, (0, 0))

    lead = kwant.Builder(kwant.TranslationalSymmetry((-lattice_spacing, 0)))
    lead.fill(template, lead_shape, (0, 0))
    syst.attach_lead(lead)
    syst.attach_lead(lead.reversed())
    return syst.finalized()


def _extract_ss(vgs_sweep, currents, ion) -> float:
    sub = [(v, i) for v, i in zip(vgs_sweep, currents) if 0 < i < 0.1 * ion]
    if len(sub) < 2:
        return float("nan")
    (v1, i1), (v2, i2) = sub[0], sub[-1]
    d_log = math.log10(i2) - math.log10(i1)
    return abs((v2 - v1) / d_log) * 1000 if d_log else float("nan")


def run(material, dft_result: DFTResult, geometry: DeviceGeometry, params: dict) -> TransportResult:
    import kwant  # local import: heavy, optional dep
    import kwant.continuum  # not re-exported by plain `import kwant` in 1.5

    handle = dft_result.tight_binding_hamiltonian
    if handle is None or handle.format != "analytic_effective_mass":
        raise ValueError(
            "kwant_backend only consumes the DFT stub's 'analytic_effective_mass' "
            "handle for now — a real Wannier90 handle needs its own loader path (M5)."
        )
    payload = handle.loader()
    m_e = payload["params"]["m_e"]
    hbar = payload["params"]["hbar"]
    band_gap_eV = payload["band_gap_eV"]

    # See _MAX_TRACTABLE_SITES above -- a fixed, coarser default than
    # channel_length/200 (which produced an intractable lattice against the
    # real solver). 0.5nm is still sub-nanometer (genuine atomistic scale
    # for a 2D-material lattice constant of ~3.2 A), just not needlessly finer.
    lattice_spacing = params.get("lattice_spacing_nm", 0.5)
    estimated_sites = (geometry.channel_length_nm / lattice_spacing) * (
        geometry.channel_width_nm / lattice_spacing
    )
    if estimated_sites > _MAX_TRACTABLE_SITES:
        raise LatticeTooLargeError(
            f"Estimated {estimated_sites:.0f} lattice sites for "
            f"{geometry.channel_length_nm}nm x {geometry.channel_width_nm}nm at "
            f"{lattice_spacing}nm spacing exceeds the tractable limit "
            f"({_MAX_TRACTABLE_SITES}) for kwant's SciPy dense fallback solver "
            f"(no MUMPS in this environment). Narrow channel_width_nm or pass a "
            f"coarser lattice_spacing_nm param."
        )

    template = kwant.continuum.discretize(payload["hamiltonian"], grid=lattice_spacing)
    syst = _build_system(kwant, template, geometry, lattice_spacing)

    vgs_sweep = params.get("vgs_sweep_V", [0.0, 0.2, 0.4, 0.6, 0.8])
    vds = params.get("vds_V", 0.05)
    # Added 2026-07-22: a second, higher V_ds point specifically to make DIBL
    # computable -- standard measurement convention pairs a low "linear
    # region" V_ds (the existing default above) with a high "saturation
    # region" one, typically V_dd. See transport/extraction.py.
    vds_high = params.get("vds_high_V", params.get("vdd_V", 0.8))
    fermi_energy = params.get("fermi_energy_eV", 0.0)
    w_um = geometry.channel_width_nm * 1e-3
    l_um = geometry.channel_length_nm * 1e-3

    def _run_sweep(vds_value: float) -> tuple[list[tuple[float, float]], list[float]]:
        iv_curve_, currents_ = [], []
        for vgs in vgs_sweep:
            smatrix = kwant.smatrix(
                syst,
                fermi_energy,
                params={"V": _make_potential(band_gap_eV, vgs, geometry), "hbar": hbar, "m_e": m_e},
            )
            transmission = smatrix.transmission(1, 0)
            current = transmission * _LANDAUER_QUANTUM * vds_value * 1e6 / w_um
            iv_curve_.append((vgs, current))
            currents_.append(current)
        return iv_curve_, currents_

    iv_curve, currents = _run_sweep(vds)
    ion, ioff = max(currents), min(currents)
    ss = _extract_ss(vgs_sweep, currents, ion)

    # Real V_th/DIBL extraction (2026-07-22) -- left None, with the reason
    # noted in extra, rather than fabricated, if this toy geometry/bias
    # range never actually crosses the constant-current criterion.
    #
    # Real, verified-by-reading-the-code limitation flagged in a 2026-08-04
    # physics-fidelity audit, not fixed here (fixing it is real NEGF
    # electrostatics work, a domain-physics scoping call -- see
    # docs/DECISIONS.md 2026-08-04): `_make_potential()` above takes only
    # `band_gap_eV` and `vgs` -- V_ds never enters the Hamiltonian/potential
    # landscape at all. `_run_sweep(vds_low)` and `_run_sweep(vds_high)`
    # therefore compute IDENTICAL transmission(V_gs) curves; the only
    # difference between them is the post-hoc linear
    # `transmission * G0 * vds_value` scaling (Landauer's I=GV). Because
    # `extract_vth_constant_current` finds V_gs at a FIXED absolute current,
    # and the high-V_ds curve is the low-V_ds curve uniformly scaled up by
    # (vds_high/vds_low), the crossing point necessarily shifts to a lower
    # V_gs at higher V_ds -- producing a nonzero, correctly-SIGNED
    # `dibl_mV_V` even though no real drain-induced barrier-lowering
    # electrostatics (self-consistent band bending under drain bias) is
    # modeled anywhere. This is a genuine artifact of the linear-response
    # Landauer scaling + log-space constant-current extraction, not a
    # measurement of the real short-channel effect -- flagged honestly via
    # `extra["dibl_caveat"]` below rather than presented as a validated
    # physical quantity.
    threshold_voltage_V: float | None = None
    dibl_mV_V: float | None = None
    vth_extraction_note = "not computed"
    try:
        vth_low = extract_vth_constant_current(vgs_sweep, currents)
        _, currents_high = _run_sweep(vds_high)
        vth_high = extract_vth_constant_current(vgs_sweep, currents_high)
        threshold_voltage_V = vth_low
        dibl_mV_V = compute_dibl_mV_per_V(vth_low, vth_high, vds, vds_high)
        vth_extraction_note = "constant_current"
    except ValueError as exc:
        vth_extraction_note = f"constant-current criterion not reached: {exc}"

    return TransportResult(
        device_geometry=geometry,
        ion_uA_per_um=ion,
        ioff_uA_per_um=ioff,
        subthreshold_swing_mV_dec=ss,
        # Ballistic NEGF transport has no mobility concept — flagged as NaN,
        # never fabricated to fill the field.
        mobility_cm2_Vs=float("nan"),
        contact_resistance_ohm_um=params.get("contact_resistance_ohm_um", float("nan")),
        # Real unit bug found and fixed in a 2026-08-04 physics-fidelity
        # audit: this divided by w_um (width), not l_um (length). ion is
        # already I_total/W (uA/um), so total power = ion*W*vds; dividing
        # that by device area (W*L) to get power PER AREA cancels the W
        # entirely, leaving ion*vds/L -- W must not appear a second time in
        # the denominator. Every downstream consumer
        # (thermal/{stub,hotspot_backend}.py) recovers total power by
        # multiplying this field by the real W*L footprint area, so the old
        # formula silently underreported total device power (and therefore
        # every downstream max_junction_temp_C) by a factor of L/W whenever
        # L != W -- e.g. 5x for this project's own 20nm x 100nm CLI-default
        # geometry (L/W = 0.2). Same dimensional-naming bug class as the
        # scattering-coefficient fix in transport/mobility_degradation.py
        # (docs/DECISIONS.md, 2026-07-31).
        power_density_W_per_um2=ion * 1e-6 * vds / l_um,
        iv_curve=iv_curve,
        threshold_voltage_V=threshold_voltage_V,
        dibl_mV_V=dibl_mV_V,
        provenance=ProvenanceInfo(backend_name="kwant_negf", is_stub=False, tool_version="kwant-1.5.0-verified"),
        extra={
            "transport_regime": "ballistic (NEGF) — mobility/Rc not physically defined by this backend",
            "contact_model": (
                "ideal semi-infinite same-material contacts (wide-band-limit-"
                "equivalent), not a real metal/2D-material contact self-energy"
            ),
            "vth_extraction_method": vth_extraction_note,
            "dibl_vds_low_V": vds,
            "dibl_vds_high_V": vds_high,
            # Found in a 2026-08-04 physics-fidelity audit -- see the
            # extended comment above dibl_mV_V's computation for the full
            # derivation. Not a claim dibl_mV_V is wrong-signed or useless,
            # just that it is NOT yet a measurement of real drain-induced
            # barrier-lowering electrostatics.
            "dibl_caveat": (
                "this backend's potential has no V_ds dependence (V_ds only "
                "scales current post-hoc via Landauer's I=GV) -- dibl_mV_V "
                "reflects that linear scaling combined with the constant-"
                "current extraction method, not real self-consistent "
                "drain-induced barrier lowering. Treat as illustrative, not "
                "validated, until the Hamiltonian/potential gains real "
                "V_ds-dependent electrostatics."
            ),
            # M9c (2026-07-27): geometry.gate_type is read and reported
            # honestly here -- every gate_type gets the identical potential
            # model above, so gate_type_physics_modeled is always False.
            # See module docstring for why an uncited "GAA is stronger"
            # multiplier isn't invented instead.
            "gate_type_requested": geometry.gate_type,
            "gate_type_physics_modeled": False,
        },
    )


class KwantTransportBackend:
    name, is_stub = "kwant", False

    def run(self, material, dft_result, geometry, params):
        return run(material, dft_result, geometry, params)
