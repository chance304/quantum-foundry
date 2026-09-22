import pytest

from quantum_foundry.dft.results import DFTResult
from quantum_foundry.dft.stub import EffectiveMassDFTStub
from quantum_foundry.materials.registry import MaterialsDB
from quantum_foundry.provenance import ProvenanceInfo
from quantum_foundry.transport.results import DeviceGeometry
from quantum_foundry.transport.stub import LongChannelMOSFETStub


def _geometry(material_id: str) -> DeviceGeometry:
    return DeviceGeometry(
        channel_length_nm=20.0,
        channel_width_nm=100.0,
        channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0,
        gate_oxide_material_id="HfO2",
        channel_material_id=material_id,
        substrate_material_id="Si",
    )


def test_stub_produces_positive_ion_and_reasonable_ss():
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    geometry = _geometry("MoS2_monolayer")

    result = LongChannelMOSFETStub().run(mos2, dft_result, geometry, {})

    assert result.ion_uA_per_um > 0
    assert result.ioff_uA_per_um > 0
    assert result.ion_uA_per_um > result.ioff_uA_per_um
    assert result.subthreshold_swing_mV_dec >= 60.0  # can't beat the Boltzmann limit
    assert result.provenance.is_stub is True
    assert len(result.iv_curve) == 11


def test_stub_mobility_scales_with_effective_mass():
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    geometry = _geometry("MoS2_monolayer")

    result = LongChannelMOSFETStub().run(mos2, dft_result, geometry, {})
    # reference mass (0.51) matches MoS2's real effective mass -> reference mobility
    assert result.mobility_cm2_Vs == 30.0


def test_carrier_type_defaults_to_electron_for_backward_compatibility():
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    geometry = _geometry("MoS2_monolayer")

    default_result = LongChannelMOSFETStub().run(mos2, dft_result, geometry, {})
    explicit_result = LongChannelMOSFETStub().run(mos2, dft_result, geometry, {"carrier_type": "electron"})
    assert default_result.mobility_cm2_Vs == explicit_result.mobility_cm2_Vs


def test_carrier_type_hole_uses_hole_effective_mass():
    db = MaterialsDB()
    ws2 = db.get("WS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(ws2, {})
    geometry = _geometry("WS2_monolayer")

    electron_result = LongChannelMOSFETStub().run(ws2, dft_result, geometry, {"carrier_type": "electron"})
    hole_result = LongChannelMOSFETStub().run(ws2, dft_result, geometry, {"carrier_type": "hole"})
    # WS2's electron and hole effective masses differ -> mobility must differ too
    assert electron_result.mobility_cm2_Vs != hole_result.mobility_cm2_Vs


def test_carrier_type_invalid_raises():
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    geometry = _geometry("MoS2_monolayer")

    with pytest.raises(ValueError, match="carrier_type"):
        LongChannelMOSFETStub().run(mos2, dft_result, geometry, {"carrier_type": "bogus"})


def test_carrier_type_hole_refuses_to_run_without_hole_effective_mass():
    # graphene_monolayer is missing effective_mass_hole in the real
    # materials DB (WSe2 used to be this test's stand-in until 2026-07-22,
    # when its real effective_mass_hole was sourced from JVASP-652 -- see
    # docs/DECISIONS.md), so EffectiveMassDFTStub already refuses to build
    # a DFTResult for a hole-role run of it (dft/stub.py's carrier-role-aware
    # gate, also added 2026-07-22 -- see docs/DECISIONS.md) -- construct a
    # DFTResult directly to verify transport/stub.py has its own
    # defense-in-depth rather than relying solely on that upstream gate.
    db = MaterialsDB()
    graphene = db.get("graphene_monolayer")
    assert graphene.effective_mass_hole is None
    dft_result = DFTResult(
        material_id=graphene.material_id,
        band_gap_eV=graphene.band_gap_eV,
        effective_mass_electron=graphene.effective_mass_electron,
        effective_mass_hole=None,
        lattice_constant_angstrom=graphene.lattice_constant_angstrom,
        tight_binding_hamiltonian=None,
        provenance=ProvenanceInfo(backend_name="test-fixture", is_stub=True, tool_version="n/a"),
    )
    geometry = _geometry("graphene_monolayer")

    with pytest.raises(ValueError, match="effective_mass_hole"):
        LongChannelMOSFETStub().run(graphene, dft_result, geometry, {"carrier_type": "hole"})


def test_defect_density_degrades_mobility_via_matthiessens_rule():
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    geometry = _geometry("MoS2_monolayer")

    baseline = LongChannelMOSFETStub().run(mos2, dft_result, geometry, {})
    degraded = LongChannelMOSFETStub().run(
        mos2, dft_result, geometry,
        {"defect_density_per_cm2": 1e11, "defect_scattering_coefficient_per_Vs": 1e15},
    )
    assert degraded.mobility_cm2_Vs < baseline.mobility_cm2_Vs
    assert degraded.extra["defect_mobility_coupling_applied"] is True
    assert baseline.extra["defect_mobility_coupling_applied"] is False


def test_power_density_depends_on_length_not_width():
    """Regression test for a real unit bug found and fixed in a 2026-08-04
    physics-fidelity audit: power_density_W_per_um2 used to divide by
    channel WIDTH a second time instead of channel LENGTH.
    ion_uA_per_um is already I_total/width, so total power = ion*width*vdd,
    and power-per-AREA (width*length) cancels width entirely, leaving
    ion*vdd/length -- width must not appear in the formula at all. Verified
    two ways: (1) power_density is invariant under changing width alone,
    (2) it matches the explicit expected formula.
    """
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})

    narrow = _geometry("MoS2_monolayer")
    wide = DeviceGeometry(
        channel_length_nm=narrow.channel_length_nm,
        channel_width_nm=narrow.channel_width_nm * 5.0,  # width changed, length unchanged
        channel_thickness_nm=narrow.channel_thickness_nm,
        gate_oxide_thickness_nm=narrow.gate_oxide_thickness_nm,
        gate_oxide_material_id=narrow.gate_oxide_material_id,
        channel_material_id=narrow.channel_material_id,
        substrate_material_id=narrow.substrate_material_id,
    )

    narrow_result = LongChannelMOSFETStub().run(mos2, dft_result, narrow, {})
    wide_result = LongChannelMOSFETStub().run(mos2, dft_result, wide, {})

    # ion_uA_per_um (current per unit width) is width-independent by
    # construction in this square-law model, so power_density -- which is
    # supposed to depend only on length -- must match exactly across widths.
    assert wide_result.power_density_W_per_um2 == pytest.approx(narrow_result.power_density_W_per_um2)

    vdd = 0.7  # transport/stub.py's own default
    l_um = narrow.channel_length_nm * 1e-3
    expected = narrow_result.ion_uA_per_um * 1e-6 * vdd / l_um
    assert narrow_result.power_density_W_per_um2 == pytest.approx(expected)


def test_defect_density_params_must_be_supplied_together():
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    geometry = _geometry("MoS2_monolayer")

    with pytest.raises(ValueError, match="together"):
        LongChannelMOSFETStub().run(mos2, dft_result, geometry, {"defect_density_per_cm2": 1e11})
    with pytest.raises(ValueError, match="together"):
        LongChannelMOSFETStub().run(
            mos2, dft_result, geometry, {"defect_scattering_coefficient_per_Vs": 1e15}
        )
