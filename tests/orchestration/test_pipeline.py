import pytest

from quantum_foundry.orchestration.config import RunConfig, StageConfig
from quantum_foundry.orchestration.pipeline import Pipeline
from quantum_foundry.transport.results import DeviceGeometry, DeviceTier


def _stub_config(material_id: str = "MoS2_monolayer") -> RunConfig:
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id=material_id, substrate_material_id="ZrO2",
    )
    return RunConfig(material_id=material_id, device_geometry=geometry)


def test_stub_pipeline_runs_end_to_end():
    result = Pipeline().run(_stub_config())

    assert result.material.material_id == "MoS2_monolayer"
    assert result.dft_result.provenance.is_stub is True
    assert result.transport_result.provenance.is_stub is True
    assert result.thermal_result.provenance.is_stub is True
    assert result.yield_result.provenance.is_stub is True
    assert result.thermal_result.max_junction_temp_C > 0
    assert 0.0 <= result.yield_result.yield_fraction <= 1.0


def test_pipeline_derives_default_stack_when_none_supplied():
    config = _stub_config()
    assert config.material_stack is None
    result = Pipeline().run(config)
    # Stack was derived from device_geometry: channel/gate_oxide/substrate
    assert result.thermal_result.extra["layers"] == ["MoS2_monolayer", "HfO2", "ZrO2"]


def test_pipeline_real_manufacturability_backend_requires_defect_density():
    config = _stub_config()
    config.manufacturability = StageConfig(backend="poisson")  # no defect_density_per_cm2
    import pytest

    with pytest.raises(ValueError, match="defect_density_per_cm2"):
        Pipeline().run(config)


def test_pipeline_dft_stub_raises_for_incomplete_material():
    import pytest

    # MoTe2 (this test's probe material until 2026-07-28) gained real
    # C2DB-sourced data that day -- see docs/DECISIONS.md and
    # mote2_monolayer.yaml. black_phosphorus_monolayer remains a genuine
    # gap (anisotropic; doesn't reduce to this schema's scalar fields).
    config = _stub_config(material_id="black_phosphorus_monolayer")
    with pytest.raises(ValueError, match="refusing to fabricate"):
        Pipeline().run(config)


def test_pipeline_populates_beol_and_m3d_budget_checks():
    result = Pipeline().run(_stub_config())
    beol = result.extra["beol_budget_check"]
    m3d = result.extra["m3d_layer_transfer_check"]
    assert beol.limit_C == 400.0
    assert m3d.limit_C == 300.0
    assert beol.actual_C == result.thermal_result.max_junction_temp_C == m3d.actual_C


# --- M9a: stacked-tier (CFET/M3D) orchestration, added 2026-07-27 ---


def _cfet_config() -> RunConfig:
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer", substrate_material_id="ZrO2",
        stacked_tiers=[
            DeviceTier(channel_material_id="MoS2_monolayer", channel_thickness_nm=0.65, carrier_type="electron"),
            DeviceTier(channel_material_id="WS2_monolayer", channel_thickness_nm=0.65, carrier_type="hole"),
        ],
    )
    return RunConfig(
        material_id="MoS2_monolayer",  # unused by the stacked path, RunConfig still requires it
        device_geometry=geometry,
        thermal=StageConfig(backend="hotspot"),
    )


def test_run_tiers_gives_each_tier_its_own_real_transport_result():
    # No HotSpot binary needed -- _run_tiers is the pure dft+transport part
    # of M9a, same "test the pure-Python part directly" split
    # thermal/hotspot_backend.py's own _write_layer_files() already uses.
    config = _cfet_config()
    tier_results = Pipeline()._run_tiers(config)

    assert len(tier_results) == 2
    assert tier_results[0].tier.channel_material_id == "MoS2_monolayer"
    assert tier_results[0].tier.carrier_type == "electron"
    assert tier_results[1].tier.channel_material_id == "WS2_monolayer"
    assert tier_results[1].tier.carrier_type == "hole"
    # Real, not coincidental: different material + different carrier role
    # must produce different transport physics, not one tier's result reused.
    assert (
        tier_results[0].transport_result.power_density_W_per_um2
        != tier_results[1].transport_result.power_density_W_per_um2
    )
    assert tier_results[0].dft_result.effective_mass_electron is not None
    assert tier_results[1].dft_result.effective_mass_hole is not None


def test_run_tiers_routes_each_tier_through_its_own_carrier_type():
    # black_phosphorus_monolayer has no real effective_mass_electron/hole
    # (genuinely anisotropic, doesn't reduce to this schema's scalar
    # fields -- see its own module note) -- if tier 1 didn't get its own
    # carrier_type routed to its own dft/stub.py call (e.g. a bug reusing
    # tier 0's electron role for every tier), this would fail for the
    # wrong reason or silently succeed. (Previously probed with
    # WSe2_monolayer; WSe2 gained a real electron mass 2026-07-28, see
    # docs/DECISIONS.md, so it no longer fails here.)
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer", substrate_material_id="ZrO2",
        stacked_tiers=[
            DeviceTier(channel_material_id="MoS2_monolayer", channel_thickness_nm=0.65, carrier_type="electron"),
            DeviceTier(channel_material_id="black_phosphorus_monolayer", channel_thickness_nm=0.65, carrier_type="electron"),
        ],
    )
    config = RunConfig(material_id="MoS2_monolayer", device_geometry=geometry, thermal=StageConfig(backend="hotspot"))
    with pytest.raises(ValueError, match="refusing to fabricate"):
        Pipeline().run(config)


def test_stacked_pipeline_requires_hotspot_thermal_backend():
    config = _cfet_config()
    config.thermal = StageConfig(backend="stub")
    with pytest.raises(ValueError, match="hotspot"):
        Pipeline().run(config)


@pytest.mark.requires_real_solver
def test_stacked_pipeline_real_run_end_to_end():
    """Real end-to-end run through Pipeline.run() -- needs the real HotSpot
    binary (not vendored in this session's fresh clone, see
    tests/e2e/test_real_pipeline.py's equivalent single-tier test). Ready to
    run the moment scripts/setup_env.sh vendors HotSpot."""
    from pathlib import Path

    from quantum_foundry.thermal.hotspot_backend import HOTSPOT_BIN

    if not Path(HOTSPOT_BIN).exists():
        pytest.skip(f"HotSpot binary not vendored at {HOTSPOT_BIN} -- run scripts/setup_env.sh")

    config = _cfet_config()
    # R_eqm(MoS2/SiO2, 300K) ~= 3.9e-8 m2*K/W, derived from Zheng, McClellan,
    # Pop & Koh, ACS Appl. Mater. Interfaces 2022 (arXiv:2204.06975): Rint~=31
    # m2*K/GW, Rint/Reqm=0.8 -- used as the best-available real analog for an
    # inter-tier bonding-dielectric interface, not a direct measurement of one
    # (see docs/M9_PLAN.md, docs/ROADMAP.md).
    config.thermal.params = {"kapitza_resistance_m2K_per_W": 3.875e-8}
    result = Pipeline().run(config)

    assert result.material.material_id == "MoS2_monolayer"  # tier 0, the documented "primary tier"
    assert len(result.extra["stacked_tier_results"]) == 2
    assert result.thermal_result.extra["n_tiers"] == 2
    assert result.thermal_result.max_junction_temp_C > 0
