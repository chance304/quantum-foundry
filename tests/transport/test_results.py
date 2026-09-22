from quantum_foundry.transport.results import DeviceGeometry, DeviceTier


def test_device_geometry_defaults_are_backward_compatible():
    # Every pre-2026-07-22 construction site omits gate_type/stacked_tiers --
    # confirms the new fields don't break them.
    geom = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    assert geom.gate_type == "single"
    assert geom.stacked_tiers is None


def test_device_geometry_stacked_tiers_round_trips():
    tiers = [
        DeviceTier(channel_material_id="MoS2_monolayer", channel_thickness_nm=0.65, carrier_type="electron"),
        DeviceTier(channel_material_id="WSe2_monolayer", channel_thickness_nm=0.65, carrier_type="hole"),
    ]
    geom = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
        gate_type="gate_all_around",
        stacked_tiers=tiers,
    )
    assert geom.gate_type == "gate_all_around"
    assert geom.stacked_tiers == tiers
    assert geom.stacked_tiers[1].carrier_type == "hole"
