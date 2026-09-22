import pytest

from quantum_foundry.dft.stub import EffectiveMassDFTStub
from quantum_foundry.materials.registry import MaterialsDB
from quantum_foundry.materials.schema import MaterialRecord


def _hole_only_material() -> MaterialRecord:
    # Synthetic fixture, not seed data: every real seeded material now has
    # both effective masses populated (WSe2 gained a real electron mass
    # 2026-07-28, the last one that didn't -- see docs/DECISIONS.md), so
    # the carrier-role-aware gate's "only one mass present" case needs a
    # hand-built record to stay tested at all, independent of the current
    # state of literature-sourced data.
    return MaterialRecord(
        material_id="synthetic_hole_only",
        formula="XY2",
        lattice_constant_angstrom=3.0,
        band_gap_eV=1.0,
        effective_mass_electron=None,
        effective_mass_hole=0.5,
    )


def test_stub_produces_real_values_from_material_record():
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    result = EffectiveMassDFTStub().run(mos2, {})

    assert result.band_gap_eV == mos2.band_gap_eV
    assert result.effective_mass_electron == mos2.effective_mass_electron
    assert result.provenance.is_stub is True
    assert result.tight_binding_hamiltonian.format == "analytic_effective_mass"


def test_stub_refuses_to_fabricate_for_incomplete_material():
    # MoTe2/WTe2 (this test's probe material until 2026-07-28) gained real
    # C2DB-sourced effective masses that day -- see docs/DECISIONS.md and
    # mote2_monolayer.yaml. black_phosphorus_monolayer remains a genuine
    # gap (anisotropic; doesn't reduce to this schema's scalar fields, see
    # its own module note) and is a safe probe.
    db = MaterialsDB()
    bp = db.get("black_phosphorus_monolayer")
    with pytest.raises(ValueError, match="refusing to fabricate"):
        EffectiveMassDFTStub().run(bp, {})


def test_tight_binding_handle_loader_returns_real_params():
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    result = EffectiveMassDFTStub().run(mos2, {})
    payload = result.tight_binding_hamiltonian.loader()
    assert payload["params"]["m_e"] == mos2.effective_mass_electron
    assert payload["band_gap_eV"] == mos2.band_gap_eV


def test_carrier_type_none_still_requires_both_masses_legacy_behavior():
    # A material with a real hole mass but no trustworthy electron mass.
    # With no carrier_type specified, the gate stays conservative and
    # requires both -- unchanged from every caller's behavior before the
    # carrier-role-aware gate existed. (Previously probed with real WSe2
    # data; WSe2 gained a real electron mass 2026-07-28, see
    # docs/DECISIONS.md, so this now uses a synthetic fixture instead.)
    material = _hole_only_material()
    with pytest.raises(ValueError, match="refusing to fabricate"):
        EffectiveMassDFTStub().run(material, {})


def test_carrier_type_hole_succeeds_for_hole_only_material():
    material = _hole_only_material()
    result = EffectiveMassDFTStub().run(material, {"carrier_type": "hole"})
    assert result.effective_mass_hole == material.effective_mass_hole
    assert result.effective_mass_electron is None
    assert result.extra["carrier_type_requested"] == "hole"
    payload = result.tight_binding_hamiltonian.loader()
    assert payload["params"]["m_e"] == material.effective_mass_hole


def test_carrier_type_electron_still_refuses_for_hole_only_material():
    material = _hole_only_material()
    with pytest.raises(ValueError, match="refusing to fabricate"):
        EffectiveMassDFTStub().run(material, {"carrier_type": "electron"})


def test_wse2_now_succeeds_in_both_roles():
    # 2026-07-28: WSe2 gained a real, cited electron mass (Kormanyos et
    # al. 2015, cross-checked against Shi et al. 2013) after its
    # previously anomalous JVASP-652 value (105.23 m0) was confirmed wrong
    # -- see docs/DECISIONS.md and wse2_monolayer.yaml. It now runs in
    # both carrier roles, unlike when this test suite was first written.
    db = MaterialsDB()
    wse2 = db.get("WSe2_monolayer")
    assert wse2.effective_mass_electron is not None
    assert wse2.effective_mass_hole is not None
    electron_result = EffectiveMassDFTStub().run(wse2, {"carrier_type": "electron"})
    hole_result = EffectiveMassDFTStub().run(wse2, {"carrier_type": "hole"})
    assert electron_result.effective_mass_electron == wse2.effective_mass_electron
    assert hole_result.effective_mass_hole == wse2.effective_mass_hole


def test_carrier_type_invalid_raises():
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    with pytest.raises(ValueError, match="carrier_type"):
        EffectiveMassDFTStub().run(mos2, {"carrier_type": "bogus"})
