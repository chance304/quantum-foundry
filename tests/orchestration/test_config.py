from quantum_foundry.orchestration.config import RunConfig, StageConfig
from quantum_foundry.transport.results import DeviceGeometry


def test_run_config_defaults_all_stages_to_stub():
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    config = RunConfig(material_id="MoS2_monolayer", device_geometry=geometry)
    assert config.dft.backend == "stub"
    assert config.transport.backend == "stub"
    assert config.thermal.backend == "stub"
    assert config.manufacturability.backend == "stub"
    assert config.material_stack is None


def test_stage_config_defaults_to_empty_params():
    sc = StageConfig(backend="devsim")
    assert sc.params == {}
