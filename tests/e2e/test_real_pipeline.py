"""Real-solver end-to-end tests — excluded from CI's lightweight job via the
`requires_real_solver` marker (see pytest.ini). See docs/DECISIONS.md for
the full 2026-07-21 install/verification story for each backend.
"""
import pytest

from quantum_foundry.transport.results import DeviceGeometry

pytestmark = pytest.mark.requires_real_solver

# A small toy geometry, deliberately narrow. A "realistic" 100nm-wide device
# at kwant_backend.py's default 0.5nm lattice spacing produces ~8000 lattice
# sites, which is intractable for kwant's SciPy dense fallback solver (no
# MUMPS in this environment) -- verified by an actual run hanging past two
# minutes before this geometry was found. See kwant_backend.py's
# LatticeTooLargeError and docs/DECISIONS.md.
_TOY_GEOMETRY = DeviceGeometry(
    channel_length_nm=10.0, channel_width_nm=5.0, channel_thickness_nm=0.65,
    gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
    channel_material_id="MoS2_monolayer",
)


def test_devsim_import_fails_in_this_sandbox_missing_blas():
    """DEVSIM's Python package installs cleanly (a real wheel, no build
    needed), but its native extension dlopen's libopenblas.so/liblapack.so/
    libblas.so at import time with standard (unmangled) symbol names. This
    sandbox has neither root access (no apt) nor conda (which provides a
    correctly-named OpenBLAS via conda-forge) -- only scipy's bundled,
    symbol-renamed OpenBLAS, which DEVSIM's loader rejects as "MISSING
    SYMBOLS". This is a sandbox-environment limitation, not a DEVSIM defect
    -- the self-hosted CI runner's conda environment (environment.yml) is
    expected to have a real OpenBLAS and should not hit this."""
    with pytest.raises(RuntimeError, match="Issues initializing DEVSIM"):
        import devsim  # noqa: F401


# test_gmsh_import_fails_in_this_sandbox_missing_libglu removed 2026-08-03:
# it asserted that importing the plain PyPI gmsh wheel fails here (real,
# still true -- libGLU.so.1 is still genuinely missing, see docs/DECISIONS.md
# 2026-07-23) but this project no longer installs that wheel at all. Since
# this test's pass/fail depended entirely on which gmsh variant happened to
# be on sys.path rather than on any code in this repo, keeping it around
# after switching to the nox build (docs/M10_PLAN.md) would just be a
# guaranteed failure once the fix is actually applied, not a meaningful
# regression guard. The real, current verification lives in
# tests/thermal/test_mesh_generation.py, which exercises the nox build this
# project now actually installs (pyproject.toml, scripts/setup_env.sh,
# .github/workflows/ci.yml).


def test_devsim_backend_not_yet_implemented():
    """devsim_backend.py's drift-diffusion equation setup is deliberately
    left as NotImplementedError -- see docs/DECISIONS.md for why. Guarded
    behind the same import-failure this sandbox hits (see test above) --
    real environments with a working DEVSIM install would reach the
    NotImplementedError instead."""
    try:
        import devsim  # noqa: F401
    except RuntimeError as exc:
        pytest.skip(f"devsim import failed in this sandbox: {exc}")

    from quantum_foundry.dft.stub import EffectiveMassDFTStub
    from quantum_foundry.materials.registry import MaterialsDB
    from quantum_foundry.transport.devsim_backend import DEVSIMTransportBackend

    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    with pytest.raises(NotImplementedError):
        DEVSIMTransportBackend().run(mos2, dft_result, _TOY_GEOMETRY, {})


def test_kwant_backend_real_run():
    """VERIFIED 2026-07-21 against a real installed kwant 1.5.0 (built from
    source in this session -- see docs/DECISIONS.md). Takes ~8s at this toy
    geometry's scale with kwant's SciPy dense fallback solver (no MUMPS).

    Updated 2026-07-22: kwant_backend.py now runs a second V_gs sweep at a
    higher V_ds specifically to extract V_th/DIBL (transport/extraction.py)
    -- roughly doubles this test's real runtime (~16s), a deliberate,
    verified trade-off for making DIBL computable at all (see docs/DECISIONS.md)."""
    pytest.importorskip("kwant")
    from quantum_foundry.dft.stub import EffectiveMassDFTStub
    from quantum_foundry.materials.registry import MaterialsDB
    from quantum_foundry.transport.kwant_backend import KwantTransportBackend

    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    result = KwantTransportBackend().run(mos2, dft_result, _TOY_GEOMETRY, {})

    assert result.provenance.is_stub is False
    assert result.ion_uA_per_um >= 0
    assert result.ioff_uA_per_um >= 0
    assert result.ion_uA_per_um >= result.ioff_uA_per_um
    assert len(result.iv_curve) == 5
    # Regression test for a real unit bug found and fixed in a 2026-08-04
    # physics-fidelity audit: power_density_W_per_um2 used to divide by
    # channel WIDTH a second time instead of channel LENGTH (ion is already
    # I_total/width, so power-per-area = ion*vds/length -- width cancels
    # entirely). _TOY_GEOMETRY here has length(10nm) != width(5nm), so this
    # would have caught the old formula's wrong result.
    vds_default = 0.05  # matches kwant_backend.py's own default
    expected_power_density = (
        result.ion_uA_per_um * 1e-6 * vds_default / (_TOY_GEOMETRY.channel_length_nm * 1e-3)
    )
    assert result.power_density_W_per_um2 == pytest.approx(expected_power_density)
    # Current should be monotonically non-decreasing with Vgs in this
    # barrier-lowering model -- a real physical sanity check, not just "it ran".
    currents = [c for _, c in result.iv_curve]
    assert currents == sorted(currents)
    # V_th/DIBL: either genuinely extracted (both real floats) or both left
    # None with a reason in extra -- never a silent partial state.
    if result.threshold_voltage_V is not None:
        assert result.dibl_mV_V is not None
        assert result.extra["vth_extraction_method"] == "constant_current"
    else:
        assert result.dibl_mV_V is None
        assert "not reached" in result.extra["vth_extraction_method"]


def test_kwant_backend_rejects_intractably_large_lattice():
    from quantum_foundry.dft.stub import EffectiveMassDFTStub
    from quantum_foundry.materials.registry import MaterialsDB
    from quantum_foundry.transport.kwant_backend import (
        KwantTransportBackend,
        LatticeTooLargeError,
    )
    from quantum_foundry.transport.results import DeviceGeometry

    pytest.importorskip("kwant")
    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    huge_geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    with pytest.raises(LatticeTooLargeError):
        KwantTransportBackend().run(mos2, dft_result, huge_geometry, {})


def test_hotspot_backend_real_run_at_cli_default_scale():
    """VERIFIED 2026-07-21 against a real built HotSpot binary, at the same
    device scale the `qf` CLI defaults to (100nm channel width, 20nm
    length) -- not just a toy geometry. Takes real wall-clock time (~60s in
    this session's sandbox) since it shells out to a real binary; this is
    exactly the kind of test that belongs behind requires_real_solver, not
    in the fast lightweight CI job. See docs/DECISIONS.md for the real
    scale-mismatch bug this uncovered and fixed (synthetic die padding)."""
    from pathlib import Path

    from quantum_foundry.dft.stub import EffectiveMassDFTStub
    from quantum_foundry.materials.registry import MaterialsDB
    from quantum_foundry.thermal.hotspot_backend import (
        HOTSPOT_BIN,
        HotSpotThermalBackend,
    )
    from quantum_foundry.thermal.stub import default_stack_from_geometry
    from quantum_foundry.transport.results import DeviceGeometry
    from quantum_foundry.transport.stub import LongChannelMOSFETStub

    if not Path(HOTSPOT_BIN).exists():
        pytest.skip(f"HotSpot binary not vendored at {HOTSPOT_BIN} -- run scripts/setup_env.sh")

    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer", substrate_material_id=None,
    )
    transport_result = LongChannelMOSFETStub().run(mos2, dft_result, geometry, {})
    stack = default_stack_from_geometry(geometry)

    result = HotSpotThermalBackend().run(transport_result, stack, {"materials_db": db})

    assert result.provenance.is_stub is False
    assert result.max_junction_temp_C > 0
    assert result.max_junction_temp_C < 200  # sanity bound, not a claimed real device limit
    assert result.extra["synthetic_die_padding_applied"] is True


def test_hotspot_backend_real_stacked_run_cfet():
    """M9b (2026-07-27, docs/M9_PLAN.md): real end-to-end run of the new
    multi-tier (CFET) thermal path against the actual HotSpot binary --
    NOT run in this session's own sandbox (no HotSpot binary vendored here,
    same as the single-tier test above -- this repo was freshly cloned for
    the M9 scoping/build work, HotSpot wasn't rebuilt in it). Written and
    unit-verified via _write_layer_files()'s own direct tests
    (tests/thermal/test_hotspot_backend.py) instead, same honesty discipline
    as every other real-solver gap in this project: ready to run the moment
    a real HotSpot binary is vendored (scripts/setup_env.sh), not presented
    as already having run."""
    from pathlib import Path

    from quantum_foundry.dft.stub import EffectiveMassDFTStub
    from quantum_foundry.materials.registry import MaterialsDB
    from quantum_foundry.thermal.hotspot_backend import (
        HOTSPOT_BIN,
        default_stacked_stack_from_geometry,
        run_stacked,
    )
    from quantum_foundry.transport.results import DeviceGeometry, DeviceTier
    from quantum_foundry.transport.stub import LongChannelMOSFETStub

    if not Path(HOTSPOT_BIN).exists():
        pytest.skip(f"HotSpot binary not vendored at {HOTSPOT_BIN} -- run scripts/setup_env.sh")

    db = MaterialsDB()
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer", substrate_material_id="ZrO2",
        stacked_tiers=[
            DeviceTier(channel_material_id="MoS2_monolayer", channel_thickness_nm=0.65, carrier_type="electron"),
            DeviceTier(channel_material_id="WS2_monolayer", channel_thickness_nm=0.65, carrier_type="hole"),
        ],
    )
    tier_results = []
    for tier in geometry.stacked_tiers:
        material = db.get(tier.channel_material_id)
        dft_result = EffectiveMassDFTStub().run(material, {"carrier_type": tier.carrier_type})
        tier_geometry = DeviceGeometry(
            channel_length_nm=geometry.channel_length_nm, channel_width_nm=geometry.channel_width_nm,
            channel_thickness_nm=tier.channel_thickness_nm, gate_oxide_thickness_nm=geometry.gate_oxide_thickness_nm,
            gate_oxide_material_id=geometry.gate_oxide_material_id, channel_material_id=tier.channel_material_id,
        )
        tier_results.append(
            LongChannelMOSFETStub().run(material, dft_result, tier_geometry, {"carrier_type": tier.carrier_type})
        )
    stack = default_stacked_stack_from_geometry(geometry)

    # Not a real citation -- placeholder pending docs/ROADMAP.md's open item to
    # source a real inter-tier R_Kapitza value, same discipline as every
    # other uncited constant in this project. This test exercises the code
    # path's mechanics, not a claimed real physical result.
    result = run_stacked(tier_results, stack, {"materials_db": db, "kapitza_resistance_m2K_per_W": 1e-8})

    assert result.provenance.is_stub is False
    assert result.max_junction_temp_C > 0
    assert result.extra["n_tiers"] == 2
    assert result.extra["kapitza_resistance_included"] is True


def test_kwant_backend_flags_gate_type_honestly():
    """M9c (2026-07-27, docs/M9_PLAN.md): geometry.gate_type is read and
    reported in extra, but NOT modeled as different physics -- no uncited
    "GAA is stronger" multiplier is invented (see kwant_backend.py's module
    docstring for why). Verifies the honest flag, not a claimed GAA effect."""
    pytest.importorskip("kwant")
    from dataclasses import replace

    from quantum_foundry.dft.stub import EffectiveMassDFTStub
    from quantum_foundry.materials.registry import MaterialsDB
    from quantum_foundry.transport.kwant_backend import KwantTransportBackend

    db = MaterialsDB()
    mos2 = db.get("MoS2_monolayer")
    dft_result = EffectiveMassDFTStub().run(mos2, {})
    gaa_geometry = replace(_TOY_GEOMETRY, gate_type="gate_all_around")

    single_gate_result = KwantTransportBackend().run(mos2, dft_result, _TOY_GEOMETRY, {})
    gaa_result = KwantTransportBackend().run(mos2, dft_result, gaa_geometry, {})

    assert single_gate_result.extra["gate_type_requested"] == "single"
    assert gaa_result.extra["gate_type_requested"] == "gate_all_around"
    assert single_gate_result.extra["gate_type_physics_modeled"] is False
    assert gaa_result.extra["gate_type_physics_modeled"] is False
    # Real, honest consequence of not modeling gate_type yet: identical
    # physics regardless of what gate_type was requested.
    assert single_gate_result.iv_curve == gaa_result.iv_curve


def test_kwant_backend_cfet_two_tiers_real_run():
    """M9c (2026-07-27, docs/M9_PLAN.md): CFET via M9a's decoupled per-tier
    orchestration, using the real Kwant backend for both tiers -- no new
    transport code was needed for this (kwant_backend.py already only ever
    modeled one planar channel per call); this test is the real proof that
    two independently-carrier-typed tiers each get a genuine, separate
    NEGF run rather than one tier's result reused for both."""
    pytest.importorskip("kwant")
    from dataclasses import replace

    from quantum_foundry.materials.registry import MaterialsDB
    from quantum_foundry.orchestration.config import RunConfig, StageConfig
    from quantum_foundry.orchestration.pipeline import Pipeline
    from quantum_foundry.transport.results import DeviceTier

    cfet_geometry = replace(
        _TOY_GEOMETRY,
        stacked_tiers=[
            DeviceTier(channel_material_id="MoS2_monolayer", channel_thickness_nm=0.65, carrier_type="electron"),
            DeviceTier(channel_material_id="WS2_monolayer", channel_thickness_nm=0.65, carrier_type="hole"),
        ],
    )
    config = RunConfig(
        material_id="MoS2_monolayer",
        device_geometry=cfet_geometry,
        dft=StageConfig(backend="stub"),
        transport=StageConfig(backend="kwant"),
    )

    tier_results = Pipeline(MaterialsDB())._run_tiers(config)

    assert len(tier_results) == 2
    assert tier_results[0].transport_result.provenance.is_stub is False
    assert tier_results[0].transport_result.provenance.backend_name == "kwant_negf"
    assert tier_results[1].transport_result.provenance.is_stub is False
    # Real, not coincidental: MoS2-electron and WS2-hole have different
    # effective masses -> different discretized Hamiltonians -> genuinely
    # different I-V curves, not one tier's NEGF result reused for the other.
    assert tier_results[0].transport_result.iv_curve != tier_results[1].transport_result.iv_curve
