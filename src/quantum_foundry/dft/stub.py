"""Stub DFT backend: parabolic/effective-mass stand-in using real
MaterialRecord fields already sourced from JARVIS-DFT/C2DB/Materials
Project — performs no ab-initio solve. Also builds an
"analytic_effective_mass" TightBindingHandle that transport/kwant_backend.py's
real NEGF backend discretizes via kwant.continuum.discretize — the concrete
bridge letting a stub DFT layer still feed a genuinely real transport
calculation.

Real ab-initio backend (Quantum ESPRESSO + Wannier90) is deferred to M5.

Carrier-role-aware gate (added 2026-07-22): `params["carrier_type"]`
("electron" | "hole" | omitted) selects which effective mass is actually
required. A material like WSe2_monolayer that has a real, cited hole mass
but no trustworthy electron mass can now run in the hole role even though
it still can't run in the electron role or with no role specified at all
(the omitted case conservatively still requires both, matching every
existing caller's behavior exactly — see docs/DECISIONS.md). Before this,
the gate required both masses unconditionally regardless of which one the
caller actually needed, which meant WSe2 couldn't run in *either* role even
after gaining a real hole mass.
"""
from __future__ import annotations

from typing import Any

from ..materials.schema import MaterialRecord
from ..provenance import ProvenanceInfo
from .results import DFTResult, TightBindingHandle

STUB_TOOL_VERSION = "effective-mass-stub-0.1"

_VALID_CARRIER_TYPES = ("electron", "hole")

# Refuses to fabricate — every field here must be a real, cited MaterialRecord
# value. If any is None (e.g. WS2_monolayer's deliberate placeholder), run()
# raises rather than substituting a made-up number. Always required
# regardless of carrier_type -- neither is carrier-specific.
_ALWAYS_REQUIRED_FIELDS = (
    "band_gap_eV",
    "lattice_constant_angstrom",
)


def _make_loader(material: MaterialRecord, carrier_type: str | None):
    # No carrier_type specified -> legacy behavior, always electron (matches
    # every pre-2026-07-22 caller exactly, see test_tight_binding_handle_loader_returns_real_params).
    effective_carrier = carrier_type or "electron"
    m = (
        material.effective_mass_electron
        if effective_carrier == "electron"
        else material.effective_mass_hole
    )
    band_gap = material.band_gap_eV

    def loader() -> dict[str, Any]:
        band_kind = "conduction" if effective_carrier == "electron" else "valence"
        return {
            "hamiltonian": "(hbar**2 / (2*m_e)) * (k_x**2 + k_y**2) + V(x, y)",
            "params": {"m_e": m, "hbar": 1.0},
            "band_gap_eV": band_gap,
            "note": (
                f"Single-band parabolic {band_kind}-band model only — no "
                f"multi-valley/spin-orbit structure. Uses "
                f"effective_mass_{effective_carrier} for this run's requested "
                f"carrier. Real ab-initio backend (Quantum ESPRESSO + "
                f"Wannier90) deferred to M5."
            ),
        }

    return loader


def run(material: MaterialRecord, params: dict) -> DFTResult:
    carrier_type = params.get("carrier_type")
    if carrier_type is not None and carrier_type not in _VALID_CARRIER_TYPES:
        raise ValueError(
            f"carrier_type must be one of {_VALID_CARRIER_TYPES} or omitted, "
            f"got {carrier_type!r}"
        )

    required = list(_ALWAYS_REQUIRED_FIELDS)
    if carrier_type is None:
        # No role specified -> conservative legacy behavior: require both,
        # unchanged from every caller's behavior before this gate existed.
        required += ["effective_mass_electron", "effective_mass_hole"]
    elif carrier_type == "electron":
        required.append("effective_mass_electron")
    else:
        required.append("effective_mass_hole")

    missing = [f for f in required if getattr(material, f) is None]
    if missing:
        raise ValueError(
            f"DFT stub requires {missing} on '{material.material_id}' "
            f"(carrier_type={carrier_type!r}) but they are None — refusing "
            f"to fabricate. Seed real materials data first (see materials/sources/)."
        )
    # Narrows the Optional fields checked above to their real (non-None)
    # type for the type checker -- the ValueError above is what actually
    # guarantees this at runtime.
    assert material.band_gap_eV is not None
    assert material.lattice_constant_angstrom is not None

    handle = TightBindingHandle(
        format="analytic_effective_mass",
        path=None,
        loader=_make_loader(material, carrier_type),
    )
    return DFTResult(
        material_id=material.material_id,
        band_gap_eV=material.band_gap_eV,
        effective_mass_electron=material.effective_mass_electron,
        effective_mass_hole=material.effective_mass_hole,
        lattice_constant_angstrom=material.lattice_constant_angstrom,
        tight_binding_hamiltonian=handle,
        provenance=ProvenanceInfo(
            backend_name="dft_stub_effective_mass",
            is_stub=True,
            tool_version=STUB_TOOL_VERSION,
        ),
        extra={
            "source_material_citations": {
                k: v.identifier for k, v in material.citations.items()
            },
            "carrier_type_requested": carrier_type,
        },
    )


class EffectiveMassDFTStub:
    name = "stub"
    is_stub = True

    def run(self, material: MaterialRecord, params: dict) -> DFTResult:
        return run(material, params)
