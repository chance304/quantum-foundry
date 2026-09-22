from quantum_foundry.dft.stub import EffectiveMassDFTStub
from quantum_foundry.materials.registry import MaterialsDB
from quantum_foundry.thermal.stub import (
    LumpedRCThermalStub,
    default_stack_from_geometry,
)
from quantum_foundry.transport.results import DeviceGeometry
from quantum_foundry.transport.stub import LongChannelMOSFETStub


def _pipeline_up_to_transport(materials_db):
    mos2 = materials_db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer", substrate_material_id="ZrO2",
    )
    transport_result = LongChannelMOSFETStub().run(mos2, dft_result, geometry, {})
    return transport_result, geometry


def test_stub_uses_real_thermal_conductivity_where_available():
    db = MaterialsDB()
    transport_result, geometry = _pipeline_up_to_transport(db)
    stack = default_stack_from_geometry(geometry)

    result = LumpedRCThermalStub().run(transport_result, stack, {}, materials_db=db)

    assert result.max_junction_temp_C > 25.0  # ambient default, should heat up under power
    assert result.thermal_resistance_K_per_W > 0
    assert result.provenance.is_stub is True
    # Channel (MoS2_monolayer) has a real cited thermal_conductivity_W_mK,
    # so it should NOT need the fallback. HfO2/ZrO2 (gate oxide/substrate)
    # don't have one seeded yet, so they correctly do.
    assert "MoS2_monolayer" not in result.extra["fallback_conductivity_used_for"]
    assert "HfO2" in result.extra["fallback_conductivity_used_for"]
    assert "ZrO2" in result.extra["fallback_conductivity_used_for"]


def test_fallback_conductivity_flagged_when_material_has_no_data():
    db = MaterialsDB()
    transport_result, geometry = _pipeline_up_to_transport(db)
    stack = default_stack_from_geometry(geometry)  # gate_oxide=HfO2, substrate=ZrO2, both null

    result = LumpedRCThermalStub().run(transport_result, stack, {}, materials_db=db)
    assert len(result.extra["fallback_conductivity_used_for"]) == 2


def test_default_stack_includes_substrate_when_present():
    db = MaterialsDB()
    _, geometry = _pipeline_up_to_transport(db)
    stack = default_stack_from_geometry(geometry)
    roles = [layer.role for layer in stack.layers]
    assert roles == ["channel", "gate_oxide", "substrate"]


def test_default_stack_omits_substrate_when_absent():
    db = MaterialsDB()
    _, geometry = _pipeline_up_to_transport(db)
    geometry.substrate_material_id = None
    stack = default_stack_from_geometry(geometry)
    roles = [layer.role for layer in stack.layers]
    assert roles == ["channel", "gate_oxide"]


def test_nm_scale_device_gets_die_area_padding_and_sane_tj():
    # Regression test for the scale-mismatch bug found while building M6:
    # a bare nm-scale device area against a 300um substrate, with no
    # lateral heat-spreading term, produced Tj in the hundreds-of-thousands
    # of degrees. The fix floors the effective area at _MIN_DIE_AREA_UM2.
    db = MaterialsDB()
    transport_result, geometry = _pipeline_up_to_transport(db)
    stack = default_stack_from_geometry(geometry)  # 20nm x 100nm channel

    result = LumpedRCThermalStub().run(transport_result, stack, {}, materials_db=db)

    assert result.extra["synthetic_die_area_padding_applied"] is True
    assert result.max_junction_temp_C < 1000.0  # physically sane, not 1e5+


def test_large_device_area_gets_no_padding():
    db = MaterialsDB()
    transport_result, geometry = _pipeline_up_to_transport(db)
    geometry.channel_length_nm = 150_000.0  # 150um -- already >= the 100um die floor
    geometry.channel_width_nm = 150_000.0
    stack = default_stack_from_geometry(geometry)

    result = LumpedRCThermalStub().run(transport_result, stack, {}, materials_db=db)

    assert result.extra["synthetic_die_area_padding_applied"] is False
