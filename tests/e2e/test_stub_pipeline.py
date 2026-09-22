"""Full end-to-end stub pipeline, via the actual `qf` CLI entrypoint —
zero install risk, the thing that should always pass regardless of which
heavy scientific packages are or aren't installed."""
from typer.testing import CliRunner

from quantum_foundry.orchestration.cli import app
from quantum_foundry.orchestration.config import RunConfig
from quantum_foundry.orchestration.pipeline import Pipeline
from quantum_foundry.transport.results import DeviceGeometry

runner = CliRunner()


def test_cli_stub_run_end_to_end():
    result = runner.invoke(app, ["run", "MoS2_monolayer", "--backend", "stub"])
    assert result.exit_code == 0


def test_pipeline_api_stub_run_end_to_end_all_provenance_is_stub():
    # MoS2_monolayer is currently the only material with a fully-populated
    # DFT-stub-required field set (band_gap/effective_mass_electron+hole/
    # lattice_constant) -- WSe2/HfO2/ZrO2/WS2 are each missing at least one.
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer", substrate_material_id=None,
    )
    config = RunConfig(material_id="MoS2_monolayer", device_geometry=geometry)
    result = Pipeline().run(config)

    for stage_result in (result.dft_result, result.transport_result, result.thermal_result, result.yield_result):
        assert stage_result.provenance.is_stub is True
