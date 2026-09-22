"""Best-effort NGMM-style chiplet-collateral export.

"chiplet collateral" is NGMM's own term (from their 3D-ADK architecture
diagram: 3D Microsystem Design = chiplet collateral + top-level information,
produced by a Customer/External Designer consuming TIE's 3D-ADK). Our
bundle format is NOT verified against any real NGMM/TIE interface spec —
see disclaimers.NGMM_SCHEMA_DISCLAIMER.

M8 (added 2026-07-22): real implementation, unblocked by M7's real
Verilog-A export (transport/verilog_a_export.py) landing the one other
missing piece -- `orchestration.pipeline.PipelineResult` has existed since
M3a. `benchmark_registry` is accepted for API compatibility but only used
for a real entry count in the summary -- real quantity-based matching
against a PipelineResult (via validation/registry.py's attach_simulated(),
which needs a SimulatedValue, a different schema than TransportResult) is
a genuine, separate cross-schema mapping design question, not invented
here. See docs/DECISIONS.md.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from ..orchestration.pipeline import PipelineResult
from ..provenance import ProvenanceInfo
from ..transport.verilog_a_export import export_verilog_a
from ..validation.registry import BenchmarkRegistry
from .disclaimers import NGMM_SCHEMA_DISCLAIMER
from .packaging_open_questions import packaging_compatibility_note


@dataclass(frozen=True)
class ChipletManifest:
    chiplet_id: str
    # e.g. "FPA Imager — Processor tier (speculative positioning, not
    # NGMM-confirmed — see docs/NGMM_COMPATIBILITY.md)"
    exemplar_tier: str
    materials_used: list[str]
    device_geometry: dict[str, Any]
    stage_provenance: dict[str, ProvenanceInfo]  # keyed by stage: dft/transport/thermal/manufacturability
    packaging_compatibility: dict[str, dict]  # keyed by material_id, from packaging_open_questions
    generated_at: str
    schema_disclaimer: str = NGMM_SCHEMA_DISCLAIMER


@dataclass(frozen=True)
class CompactModelStub:
    # "placeholder" (real Verilog-A export failed, e.g. too few iv_curve
    # points) or "verilog_a" (real, M7's transport/verilog_a_export.py).
    format: str
    is_placeholder: bool
    content: str  # raw file content — never a claim of EDA-import-readiness while is_placeholder


@dataclass(frozen=True)
class ChipletCollateralBundle:
    manifest: ChipletManifest
    compact_model: CompactModelStub
    summary_markdown: str
    provenance: ProvenanceInfo


def export_chiplet_collateral(
    pipeline_result: PipelineResult,
    exemplar_tier: str,
    benchmark_registry: BenchmarkRegistry | None = None,
    vds_V: float = 0.05,
) -> ChipletCollateralBundle:
    material = pipeline_result.material
    geom = pipeline_result.transport_result.device_geometry

    stage_provenance = {
        "dft": pipeline_result.dft_result.provenance,
        "transport": pipeline_result.transport_result.provenance,
        "thermal": pipeline_result.thermal_result.provenance,
        "manufacturability": pipeline_result.yield_result.provenance,
    }
    packaging_compatibility = {
        material.material_id: packaging_compatibility_note(material.material_id, material.formula),
    }
    device_geometry = {
        "channel_length_nm": geom.channel_length_nm,
        "channel_width_nm": geom.channel_width_nm,
        "channel_thickness_nm": geom.channel_thickness_nm,
        "gate_oxide_thickness_nm": geom.gate_oxide_thickness_nm,
        "gate_oxide_material_id": geom.gate_oxide_material_id,
        "channel_material_id": geom.channel_material_id,
        "substrate_material_id": geom.substrate_material_id,
        "gate_type": geom.gate_type,
    }

    try:
        va_content = export_verilog_a(material.material_id, pipeline_result.transport_result, vds_V=vds_V)
        compact_model = CompactModelStub(format="verilog_a", is_placeholder=False, content=va_content)
    except ValueError as exc:
        # Refuses to fabricate a compact model from too little data (M7's
        # own refusal, e.g. <2 iv_curve points) rather than crash the whole
        # export -- degrades to an honestly-labeled placeholder instead.
        compact_model = CompactModelStub(
            format="placeholder",
            is_placeholder=True,
            content=f"# Real Verilog-A export failed: {exc}\n",
        )

    manifest = ChipletManifest(
        chiplet_id=f"{material.material_id}_{pipeline_result.generated_at.strftime('%Y%m%dT%H%M%SZ')}",
        exemplar_tier=exemplar_tier,
        materials_used=[material.material_id],
        device_geometry=device_geometry,
        stage_provenance=stage_provenance,
        packaging_compatibility=packaging_compatibility,
        generated_at=pipeline_result.generated_at.isoformat(),
    )

    summary_lines = [
        f"# Chiplet Collateral Summary: {manifest.chiplet_id}",
        "",
        f"Exemplar tier: {exemplar_tier}",
        f"Material(s): {', '.join(manifest.materials_used)}",
        (f"Compact model: {compact_model.format} "
        f"({'PLACEHOLDER -- not a real netlist' if compact_model.is_placeholder else 'real behavioral Verilog-A, not simulator-verified'})"),
    ]
    if benchmark_registry is not None:
        summary_lines.append(
            f"Benchmark registry supplied: {len(benchmark_registry.all_entries())} entries "
            f"(not yet matched against this run -- see module docstring)."
        )
    summary_lines += ["", NGMM_SCHEMA_DISCLAIMER]

    return ChipletCollateralBundle(
        manifest=manifest,
        compact_model=compact_model,
        summary_markdown="\n".join(summary_lines) + "\n",
        provenance=ProvenanceInfo(
            backend_name="chiplet_collateral_export",
            # Real bug found in a 2026-08-04 physics-fidelity audit: this
            # previously read ONLY transport_result.provenance.is_stub,
            # silently ignoring dft/thermal/manufacturability. Today every
            # real pipeline run has dft.backend="stub" (no real ab-initio
            # backend exists yet -- see dft/stub.py), so a run with real
            # transport/thermal/yield backends (kwant/hotspot/poisson) would
            # have reported is_stub=False here -- claiming the whole bundle
            # (including the DFT-stub-derived band structure every other
            # stage is built on) was fully real. The bundle is only as real
            # as its least-real input: True if ANY stage's provenance is a
            # stub, matching stage_provenance's own per-stage detail below.
            is_stub=any(p.is_stub for p in stage_provenance.values()),
            tool_version="chiplet-export-0.1",
        ),
    )


def write_bundle(bundle: ChipletCollateralBundle, out_dir: Path) -> Path:
    """Writes manifest.yaml, a compact-model file, and SUMMARY.md into
    out_dir. The compact-model file is named `compact_model.va` when it's
    real (`format == "verilog_a"`) and `compact_model.stub` when it's still
    a placeholder -- never named `.va`/`.sp` while `is_placeholder` is True,
    so it can never be mistaken for an EDA-importable netlist.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(asdict(bundle.manifest), sort_keys=False))

    model_ext = "va" if bundle.compact_model.format == "verilog_a" else "stub"
    model_path = out_dir / f"compact_model.{model_ext}"
    model_path.write_text(bundle.compact_model.content)

    summary_path = out_dir / "SUMMARY.md"
    summary_path.write_text(bundle.summary_markdown)

    return out_dir
