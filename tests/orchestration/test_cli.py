from typer.testing import CliRunner

from quantum_foundry.orchestration.cli import app

runner = CliRunner()


def test_run_stub_prints_summary():
    result = runner.invoke(app, ["run", "MoS2_monolayer", "--backend", "stub"])
    assert result.exit_code == 0
    assert "Ion=" in result.stdout
    assert "Tj=" in result.stdout
    assert "Yield=" in result.stdout


def test_run_surfaces_beol_and_m3d_budget_checks():
    result = runner.invoke(app, ["run", "MoS2_monolayer", "--backend", "stub"])
    assert result.exit_code == 0
    assert "BEOL Cu/low-k thermal budget (400C):" in result.stdout
    assert "M3D layer-transfer thermal budget (300C):" in result.stdout
    assert "PASS" in result.stdout  # a stub-scale run stays well under both limits


def test_run_unknown_material_fails_cleanly():
    result = runner.invoke(app, ["run", "Unobtainium_monolayer", "--backend", "stub"])
    assert result.exit_code != 0


def test_export_verilog_a_prints_real_module():
    result = runner.invoke(app, ["export-verilog-a", "MoS2_monolayer"])
    assert result.exit_code == 0
    assert "module qf_MoS2_monolayer_behavioral(d, g, s);" in result.stdout
    assert "endmodule" in result.stdout
    assert '`include "disciplines.vams"' in result.stdout


def test_export_verilog_a_writes_to_file(tmp_path):
    out_path = tmp_path / "mos2.va"
    result = runner.invoke(app, ["export-verilog-a", "MoS2_monolayer", "--out", str(out_path)])
    assert result.exit_code == 0
    assert out_path.exists()
    assert "endmodule" in out_path.read_text()


def test_export_chiplet_writes_real_bundle(tmp_path):
    out_dir = tmp_path / "collateral"
    result = runner.invoke(app, ["export-chiplet", "MoS2_monolayer", "--out-dir", str(out_dir)])
    assert result.exit_code == 0
    assert (out_dir / "manifest.yaml").exists()
    assert (out_dir / "compact_model.va").exists()
    assert (out_dir / "SUMMARY.md").exists()
    assert "real" in result.stdout


def test_calibrate_recovers_known_inputs():
    result = runner.invoke(app, ["calibrate", "MoS2_monolayer"])
    assert result.exit_code == 0
    assert "Self-consistency check" in result.stdout
    assert "TLM extraction:" in result.stdout
    assert "van der Pauw extraction:" in result.stdout
    # Default sheet_resistance_ohm_sq is 500.0 -- both extractions should
    # recover it closely (self-consistency, not new physics).
    assert "Rsheet=500.00" in result.stdout
