"""Real behavior tests for chiplet_export.py -- M8, unblocked 2026-07-22 by
M3 (PipelineResult, already existed) + M7 (real Verilog-A export)."""
from dataclasses import replace

import yaml

from quantum_foundry.ngmm_compat.chiplet_export import (
    ChipletCollateralBundle,
    ChipletManifest,
    CompactModelStub,
    export_chiplet_collateral,
    write_bundle,
)
from quantum_foundry.orchestration.config import RunConfig
from quantum_foundry.orchestration.pipeline import Pipeline
from quantum_foundry.provenance import ProvenanceInfo
from quantum_foundry.transport.results import DeviceGeometry, TransportResult


def _mos2_pipeline_result():
    geometry = DeviceGeometry(
        channel_length_nm=20.0, channel_width_nm=100.0, channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0, gate_oxide_material_id="HfO2",
        channel_material_id="MoS2_monolayer",
    )
    return Pipeline().run(RunConfig(material_id="MoS2_monolayer", device_geometry=geometry))


def test_chiplet_manifest_dataclass_shape():
    manifest = ChipletManifest(
        chiplet_id="test-chiplet-1",
        exemplar_tier="FPA Imager — Processor tier (speculative, not NGMM-confirmed)",
        materials_used=["MoS2_monolayer"],
        device_geometry={"channel_length_nm": 120},
        stage_provenance={"dft": ProvenanceInfo(backend_name="stub", is_stub=True)},
        packaging_compatibility={"MoS2_monolayer": {"status": "unresolved_open_question"}},
        generated_at="2026-07-20T00:00:00Z",
    )
    assert manifest.chiplet_id == "test-chiplet-1"
    assert "speculative" in manifest.exemplar_tier
    assert manifest.schema_disclaimer  # inherited default


def test_compact_model_stub_placeholder_is_never_a_real_extension():
    stub = CompactModelStub(format="placeholder", is_placeholder=True, content="# not a real netlist yet")
    assert stub.is_placeholder is True
    assert stub.format == "placeholder"


def test_export_chiplet_collateral_real_run_produces_real_verilog_a():
    result = _mos2_pipeline_result()
    bundle = export_chiplet_collateral(result, exemplar_tier="FPA Imager — Processor tier (speculative)")

    assert bundle.compact_model.format == "verilog_a"
    assert bundle.compact_model.is_placeholder is False
    assert "endmodule" in bundle.compact_model.content

    assert set(bundle.manifest.stage_provenance) == {"dft", "transport", "thermal", "manufacturability"}
    for provenance in bundle.manifest.stage_provenance.values():
        assert isinstance(provenance, ProvenanceInfo)

    assert bundle.manifest.packaging_compatibility["MoS2_monolayer"]["status"] == "unresolved_open_question"
    assert bundle.manifest.materials_used == ["MoS2_monolayer"]
    assert "MoS2_monolayer" in bundle.summary_markdown
    assert bundle.provenance.backend_name == "chiplet_collateral_export"


def test_export_chiplet_collateral_is_stub_if_any_stage_is_stub_even_when_transport_is_real():
    """Regression test for a real bug found in a 2026-08-04 physics-fidelity
    audit: the bundle's own provenance.is_stub previously read ONLY
    transport_result.provenance.is_stub, ignoring dft/thermal/manufacturability.
    Every real pipeline run today still has dft.backend="stub" (no real
    ab-initio backend exists yet), so a mixed run with a real transport
    backend (e.g. kwant) would have wrongly reported is_stub=False for the
    whole bundle -- claiming full-real provenance for collateral that was
    still built on a stub band-structure/effective-mass model underneath.
    The rolled-up flag must be True whenever ANY stage is a stub, matching
    the per-stage detail already carried in stage_provenance.
    """
    result = _mos2_pipeline_result()
    # dft stays real=False (default stub) -- simulate every OTHER stage
    # having actually run a real backend, the scenario the old code got wrong.
    result.transport_result = replace(
        result.transport_result,
        provenance=ProvenanceInfo(backend_name="kwant_negf", is_stub=False),
    )
    result.thermal_result = replace(
        result.thermal_result,
        provenance=ProvenanceInfo(backend_name="hotspot", is_stub=False),
    )
    result.yield_result = replace(
        result.yield_result,
        provenance=ProvenanceInfo(backend_name="poisson_yield", is_stub=False),
    )
    assert result.dft_result.provenance.is_stub is True  # sanity: dft is still the stub

    bundle = export_chiplet_collateral(result, exemplar_tier="test tier")

    assert bundle.provenance.is_stub is True, (
        "bundle.provenance.is_stub must be True when ANY stage (here: dft) "
        "is a stub, even if transport/thermal/manufacturability are all real"
    )


def test_export_chiplet_collateral_is_not_stub_when_every_stage_is_real():
    result = _mos2_pipeline_result()
    result.dft_result = replace(
        result.dft_result, provenance=ProvenanceInfo(backend_name="dft_real", is_stub=False)
    )
    result.transport_result = replace(
        result.transport_result, provenance=ProvenanceInfo(backend_name="kwant_negf", is_stub=False)
    )
    result.thermal_result = replace(
        result.thermal_result, provenance=ProvenanceInfo(backend_name="hotspot", is_stub=False)
    )
    result.yield_result = replace(
        result.yield_result, provenance=ProvenanceInfo(backend_name="poisson_yield", is_stub=False)
    )

    bundle = export_chiplet_collateral(result, exemplar_tier="test tier")

    assert bundle.provenance.is_stub is False


def test_export_chiplet_collateral_degrades_to_placeholder_when_iv_curve_too_sparse():
    result = _mos2_pipeline_result()
    sparse_transport = TransportResult(
        device_geometry=result.transport_result.device_geometry,
        ion_uA_per_um=1.0, ioff_uA_per_um=0.1, subthreshold_swing_mV_dec=70.0,
        mobility_cm2_Vs=30.0, contact_resistance_ohm_um=1000.0, power_density_W_per_um2=1e-6,
        iv_curve=[(0.0, 0.0)],  # only 1 point -- too sparse for export_verilog_a
        provenance=ProvenanceInfo(backend_name="test", is_stub=True),
    )
    result.transport_result = sparse_transport
    bundle = export_chiplet_collateral(result, exemplar_tier="test tier")

    assert bundle.compact_model.format == "placeholder"
    assert bundle.compact_model.is_placeholder is True
    assert "Real Verilog-A export failed" in bundle.compact_model.content


def test_write_bundle_names_compact_model_va_when_real(tmp_path):
    result = _mos2_pipeline_result()
    bundle = export_chiplet_collateral(result, exemplar_tier="test tier")
    out = write_bundle(bundle, tmp_path)

    assert out == tmp_path
    assert (tmp_path / "compact_model.va").exists()
    assert not (tmp_path / "compact_model.stub").exists()
    assert (tmp_path / "SUMMARY.md").exists()

    manifest_data = yaml.safe_load((tmp_path / "manifest.yaml").read_text())
    assert manifest_data["materials_used"] == ["MoS2_monolayer"]
    assert manifest_data["packaging_compatibility"]["MoS2_monolayer"]["status"] == "unresolved_open_question"


def test_write_bundle_names_compact_model_stub_when_placeholder(tmp_path):
    manifest = ChipletManifest(
        chiplet_id="x", exemplar_tier="x", materials_used=[], device_geometry={},
        stage_provenance={}, packaging_compatibility={}, generated_at="x",
    )
    placeholder = CompactModelStub(format="placeholder", is_placeholder=True, content="# not real")
    bundle = ChipletCollateralBundle(
        manifest=manifest, compact_model=placeholder, summary_markdown="summary",
        provenance=ProvenanceInfo(backend_name="test", is_stub=True),
    )
    write_bundle(bundle, tmp_path)

    assert (tmp_path / "compact_model.stub").exists()
    assert not (tmp_path / "compact_model.va").exists()
