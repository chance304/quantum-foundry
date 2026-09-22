"""Stub transport backend: closed-form long-channel square-law MOSFET
equations. Not geometry-accurate (no short-channel effects, no ballistic
transport) — that gap is exactly what devsim_backend.py/kwant_backend.py
exist to fill.

Real design point added 2026-07-21 while building orchestration/
heterostructure.py: `params["carrier_type"]` selects electron ("electron",
default, an n-type/nFET calculation using effective_mass_electron) or hole
("hole", a p-type/pFET calculation using effective_mass_hole) transport.
Without this, every call implicitly modeled an nFET regardless of which
carrier actually dominates conduction in the material/polarity being
searched for -- a real gap, not a hypothetical one, since a genuine n/p
CMOS-pairing search (the "close the n/p asymmetry gap"
framing) is meaningless if every candidate is scored as if it were n-type.
"""
from __future__ import annotations

from ..dft.results import DFTResult
from ..materials.schema import MaterialRecord
from ..provenance import ProvenanceInfo
from .mobility_degradation import defect_limited_mobility, matthiessens_rule_mobility
from .results import DeviceGeometry, TransportResult

STUB_TOOL_VERSION = "long-channel-mosfet-stub-0.1"
_REFERENCE_MOBILITY_CM2_VS = 30.0  # order-of-magnitude back-gated MoS2 FET literature value
_REFERENCE_EFFECTIVE_MASS = 0.51  # matches MoS2_monolayer's real effective_mass_electron

_VALID_CARRIER_TYPES = ("electron", "hole")


def run(
    material: MaterialRecord,
    dft_result: DFTResult,
    geometry: DeviceGeometry,
    params: dict,
) -> TransportResult:
    carrier_type = params.get("carrier_type", "electron")
    if carrier_type not in _VALID_CARRIER_TYPES:
        raise ValueError(f"carrier_type must be one of {_VALID_CARRIER_TYPES}, got {carrier_type!r}")

    m = dft_result.effective_mass_electron if carrier_type == "electron" else dft_result.effective_mass_hole
    if m is None:
        raise ValueError(
            f"'{material.material_id}' has no effective_mass_{'electron' if carrier_type == 'electron' else 'hole'} "
            f"-- cannot run a {carrier_type} transport calculation. Not fabricating a value."
        )
    mobility = _REFERENCE_MOBILITY_CM2_VS * (_REFERENCE_EFFECTIVE_MASS / m)

    # Defect-density -> mobility coupling (added 2026-07-22, see
    # mobility_degradation.py): both params required together, or neither --
    # supplying only one is refused rather than silently ignored, mirroring
    # carrier_type's own validation style above.
    defect_density = params.get("defect_density_per_cm2")
    scattering_coefficient = params.get("defect_scattering_coefficient_per_Vs")
    if (defect_density is None) != (scattering_coefficient is None):
        raise ValueError(
            "defect_density_per_cm2 and defect_scattering_coefficient_per_Vs "
            "must be supplied together, or not at all -- got only one."
        )
    defect_mobility_applied = defect_density is not None
    if defect_mobility_applied:
        # Narrows both to float for the type checker -- the XOR check above
        # is what actually guarantees this at runtime.
        assert defect_density is not None and scattering_coefficient is not None
        mu_defect = defect_limited_mobility(defect_density, scattering_coefficient)
        mobility = matthiessens_rule_mobility(mobility, mu_defect)

    vdd = params.get("vdd_V", 0.7)
    vt = params.get("vth_V", 0.3)
    l_um = geometry.channel_length_nm * 1e-3
    # cox_F_per_cm2 is NOT a citation — an order-of-magnitude placeholder.
    # A real value is a DEVSIM-derived (or MOS-capacitor-measured) quantity.
    cox = params.get("cox_F_per_cm2", 2e-6)

    k = mobility * cox
    ion = 0.5 * k * (vdd - vt) ** 2 / l_um * 1e6  # uA/um, order-of-magnitude
    ss = 60.0 * (1.0 + params.get("ss_nonideality", 0.5))  # mV/dec
    ioff = ion * 10 ** (-(vt * 1000) / ss)
    # contact_resistance_ohm_um is NOT a citation — order-of-magnitude default.
    rc = params.get("contact_resistance_ohm_um", 1000.0)
    # Real unit bug found and fixed in a 2026-08-04 physics-fidelity audit:
    # this divided by w_um (width), not l_um (length) -- same class of bug
    # as kwant_backend.py's identical mistake (see that module for the full
    # derivation). ion is already I_total/W (uA/um); total power =
    # ion*W*vdd, and power PER AREA (W*L) cancels W entirely, leaving
    # ion*vdd/L. Dividing by w_um a second time silently underreported
    # power_density_W_per_um2 (and therefore every downstream
    # max_junction_temp_C) by a factor of L/W whenever L != W.
    power = (ion * 1e-6) * vdd / l_um

    iv_curve = [
        (v, max(0.0, k * (v - vt)) * 1e6 if v > vt else ioff)
        for v in [i * vdd / 10 for i in range(11)]
    ]

    return TransportResult(
        device_geometry=geometry,
        ion_uA_per_um=ion,
        ioff_uA_per_um=ioff,
        subthreshold_swing_mV_dec=ss,
        mobility_cm2_Vs=mobility,
        contact_resistance_ohm_um=rc,
        power_density_W_per_um2=power,
        iv_curve=iv_curve,
        provenance=ProvenanceInfo(
            backend_name="transport_stub_long_channel",
            is_stub=True,
            tool_version=STUB_TOOL_VERSION,
        ),
        extra={
            "model": "square-law long-channel, non-geometry-accurate",
            "defect_mobility_coupling_applied": defect_mobility_applied,
        },
    )


class LongChannelMOSFETStub:
    name = "stub"
    is_stub = True

    def run(self, material, dft_result, geometry, params):
        return run(material, dft_result, geometry, params)
