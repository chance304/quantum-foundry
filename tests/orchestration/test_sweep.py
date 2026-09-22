from quantum_foundry.orchestration.config import RunConfig
from quantum_foundry.orchestration.sweep import sweep
from quantum_foundry.transport.results import DeviceGeometry


def test_sweep_varies_param_across_runs():
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    base_config = RunConfig(material_id="MoS2_monolayer", device_geometry=geometry)

    results = sweep(base_config, stage="transport", param="vdd_V", values=[0.5, 0.7, 0.9])

    assert len(results) == 3
    # Higher vdd should generally increase Ion (square-law stub model)
    ions = [r.transport_result.ion_uA_per_um for r in results]
    assert ions[2] > ions[0]
    # base_config itself must be untouched (deep-copied per iteration)
    assert "vdd_V" not in base_config.transport.params
