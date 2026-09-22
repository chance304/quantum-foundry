"""`qf` CLI entrypoint (wired in pyproject.toml as quantum_foundry.orchestration.cli:app).

Known gap: real (`--backend real`) runs need a validated defect_density_per_cm2
source (CLI param or config file), not the None placeholder below —
manufacturability.poisson_murphy correctly raises if it's never supplied, so
this fails loudly rather than silently, but the UX still needs finishing.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import typer

from ..ngmm_compat.chiplet_export import export_chiplet_collateral, write_bundle
from ..transport.results import DeviceGeometry
from ..transport.verilog_a_export import export_verilog_a
from ..validation.pcm_structures import (
    extract_tlm_parameters,
    extract_van_der_pauw_sheet_resistance,
    synthesize_tlm_measurements,
    synthesize_van_der_pauw_measurement,
)
from .config import RunConfig, StageConfig
from .heterostructure import search as heterostructure_search
from .pipeline import Pipeline
from .report import render_ppa_y_markdown

app = typer.Typer()
_PREFLIGHT = Path(__file__).parents[3] / "scripts" / "preflight.sh"


def _require_preflight() -> None:
    if subprocess.call(["sh", str(_PREFLIGHT)]) != 0:
        typer.echo(
            "Real-backend prerequisites missing — refusing --backend real. "
            "Run `qf preflight` for details.",
            err=True,
        )
        raise typer.Exit(1)


@app.command()
def run(
    material: str,
    backend: str = "stub",
    channel_length_nm: float = 20.0,
    channel_width_nm: float = 100.0,
    gate_oxide_material: str = "HfO2",
    substrate_material: str = "Si",
) -> None:
    if backend != "stub":
        _require_preflight()

    geometry = DeviceGeometry(
        channel_length_nm=channel_length_nm,
        channel_width_nm=channel_width_nm,
        channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0,
        gate_oxide_material_id=gate_oxide_material,
        channel_material_id=material,
        substrate_material_id=substrate_material,
    )
    config = RunConfig(
        material_id=material,
        device_geometry=geometry,
        dft=StageConfig(backend="stub"),  # DFT stays stub in Phase-1 regardless of --backend
        transport=StageConfig(backend=backend),
        thermal=StageConfig(backend="hotspot" if backend != "stub" else "stub"),
        manufacturability=StageConfig(
            backend="poisson" if backend != "stub" else "stub",
            params={} if backend == "stub" else {"defect_density_per_cm2": None},
        ),
    )
    result = Pipeline().run(config)
    typer.echo(
        f"Ion={result.transport_result.ion_uA_per_um:.3g} uA/um  "
        f"Tj={result.thermal_result.max_junction_temp_C:.1f} C  "
        f"Yield={result.yield_result.yield_fraction:.3f}"
    )
    # Added 2026-07-22: PipelineResult.extra's BEOL/M3D checks were computed
    # every run but never surfaced here -- always shown, not just on
    # failure, matching this project's "never hide a gap" discipline.
    for check in (result.extra["beol_budget_check"], result.extra["m3d_layer_transfer_check"]):
        status = "PASS" if check.passed else "FAIL"
        typer.echo(f"{check.limit_name} ({check.limit_C:.0f}C): {status} (margin {check.margin_C:+.1f}C)")


@app.command()
def preflight() -> None:
    raise typer.Exit(subprocess.call(["sh", str(_PREFLIGHT)]))


@app.command(name="export-verilog-a")
def export_verilog_a_cmd(
    material: str,
    backend: str = "stub",
    vds_v: float = 0.05,
    channel_length_nm: float = 20.0,
    channel_width_nm: float = 100.0,
    out: str | None = None,
) -> None:
    """M7: real behavioral (piecewise-linear lookup-table) Verilog-A export
    from a material's simulated I(Vgs) curve -- see
    transport/verilog_a_export.py's module docstring for the scope
    decision (behavioral/LUT, not a BSIM-CMG parameter fit)."""
    if backend != "stub":
        _require_preflight()

    geometry = DeviceGeometry(
        channel_length_nm=channel_length_nm,
        channel_width_nm=channel_width_nm,
        channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0,
        gate_oxide_material_id="HfO2",
        channel_material_id=material,
    )
    config = RunConfig(material_id=material, device_geometry=geometry, transport=StageConfig(backend=backend))
    result = Pipeline().run(config)
    va = export_verilog_a(material, result.transport_result, vds_V=vds_v)

    if out:
        Path(out).write_text(va)
        typer.echo(f"Wrote {out}")
    else:
        typer.echo(va)


@app.command(name="export-chiplet")
def export_chiplet_cmd(
    material: str,
    exemplar_tier: str = "unspecified (speculative -- see docs/NGMM_COMPATIBILITY.md)",
    backend: str = "stub",
    out_dir: str = "./chiplet_collateral",
    channel_length_nm: float = 20.0,
    channel_width_nm: float = 100.0,
) -> None:
    """M8: real NGMM-style chiplet-collateral export (manifest.yaml,
    compact_model.va|.stub, SUMMARY.md) -- see
    ngmm_compat/chiplet_export.py's module docstring for the real scope
    (unverified against any real NGMM/TIE schema, see disclaimers.py)."""
    if backend != "stub":
        _require_preflight()

    geometry = DeviceGeometry(
        channel_length_nm=channel_length_nm,
        channel_width_nm=channel_width_nm,
        channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0,
        gate_oxide_material_id="HfO2",
        channel_material_id=material,
    )
    config = RunConfig(material_id=material, device_geometry=geometry, transport=StageConfig(backend=backend))
    result = Pipeline().run(config)
    bundle = export_chiplet_collateral(result, exemplar_tier=exemplar_tier)
    written_dir = write_bundle(bundle, Path(out_dir))

    typer.echo(
        f"Wrote chiplet collateral to {written_dir} "
        f"(compact model: {bundle.compact_model.format}, "
        f"{'PLACEHOLDER' if bundle.compact_model.is_placeholder else 'real'})"
    )


@app.command()
def calibrate(
    material: str,
    channel_width_um: float = 1.0,
    sheet_resistance_ohm_sq: float = 500.0,
    spacings_um: str = "2,5,10,20",
    vdp_asymmetry_ratio: float = 1.0,
) -> None:
    """Synthetic PCM calibration self-check (TLM + van der Pauw,
    validation/pcm_structures.py). Takes this pipeline's real (or
    backend-dependent placeholder) contact_resistance_ohm_um, synthesizes
    what a real TLM/van der Pauw structure would measure, and confirms the
    standard extraction algorithms recover it. Proves the extraction math
    is implemented correctly -- NOT a claim that sheet_resistance_ohm_sq
    below is a real cited value (same "order-of-magnitude placeholder, not
    a citation" convention as transport/stub.py's cox_F_per_cm2).
    """
    geometry = DeviceGeometry(
        channel_length_nm=20.0,
        channel_width_nm=channel_width_um * 1000.0,
        channel_thickness_nm=0.65,
        gate_oxide_thickness_nm=2.0,
        gate_oxide_material_id="HfO2",
        channel_material_id=material,
    )
    config = RunConfig(material_id=material, device_geometry=geometry)
    result = Pipeline().run(config)
    rc = result.transport_result.contact_resistance_ohm_um

    if not math.isfinite(rc):
        typer.echo(
            f"contact_resistance_ohm_um is not finite ({rc}) for this backend "
            f"-- cannot run a meaningful calibration self-check.",
            err=True,
        )
        raise typer.Exit(1)

    spacings = [float(s) for s in spacings_um.split(",")]
    tlm_measurements = synthesize_tlm_measurements(sheet_resistance_ohm_sq, rc, channel_width_um, spacings)
    tlm_extracted = extract_tlm_parameters(tlm_measurements, channel_width_um)

    r_a, r_b = synthesize_van_der_pauw_measurement(sheet_resistance_ohm_sq, vdp_asymmetry_ratio)
    vdp_extracted_rsheet = extract_van_der_pauw_sheet_resistance(r_a, r_b)

    typer.echo(
        "Self-consistency check, not a new physics claim: this validates the "
        "extraction math against a known input, it does not measure real silicon."
    )
    typer.echo(f"Input:  Rc={rc:.2f} ohm*um (from pipeline)  Rsheet={sheet_resistance_ohm_sq:.2f} ohm/sq (NOT a citation)")
    typer.echo(
        f"TLM extraction:          Rsheet={tlm_extracted.sheet_resistance_ohm_sq:.2f} ohm/sq  "
        f"Rc={tlm_extracted.contact_resistance_ohm_um:.2f} ohm*um"
    )
    typer.echo(f"van der Pauw extraction: Rsheet={vdp_extracted_rsheet:.2f} ohm/sq")


@app.command(name="heterostructure-search")
def heterostructure_search_cmd(format: str = "text") -> None:
    """n/p channel-material search (M6) -- see heterostructure.py's
    docstring for the honest scope note (channel-material search, not a
    literal bonded-heterostructure simulation).

    --format markdown (added 2026-07-22) renders a real PPA-Y Pareto-matrix
    report (orchestration/report.py) instead of the plain text below.
    """
    if format not in ("text", "markdown"):
        typer.echo(f"--format must be 'text' or 'markdown', got {format!r}", err=True)
        raise typer.Exit(1)

    result = heterostructure_search()

    if format == "markdown":
        typer.echo(render_ppa_y_markdown(result))
        return

    typer.echo(
        "NOTE: Tj values below come from thermal/stub.py's lumped-RC model, "
        "not the real HotSpot backend -- at this device's nm-scale area vs. "
        "a bulk substrate thickness, the stub's 1D series-resistance model "
        "has no lateral heat-spreading term (the same scale-mismatch class "
        "fixed for the real HotSpot backend via _pad_to_die_footprint(), "
        "left unaddressed here). Treat Tj as an ordinal signal only, not a "
        "physically meaningful absolute temperature -- see docs/ROADMAP.md."
    )

    for role, candidates, front, recommended in (
        ("n-type", result.n_candidates, result.n_pareto_front, result.recommended_n_material_id),
        ("p-type", result.p_candidates, result.p_pareto_front, result.recommended_p_material_id),
    ):
        typer.echo(f"\n=== {role} role ===")
        for c in candidates:
            if c.pipeline_result is None:
                typer.echo(f"  {c.material_id}: EXCLUDED — {c.excluded_reason}")
            else:
                r = c.pipeline_result
                on_front = " [pareto-front]" if r in front else ""
                typer.echo(
                    f"  {c.material_id}: Ion={r.transport_result.ion_uA_per_um:.3g} uA/um  "
                    f"Tj={r.thermal_result.max_junction_temp_C:.1f} C  "
                    f"Yield={r.yield_result.yield_fraction:.3f}{on_front}"
                )
        if recommended:
            typer.echo(f"  -> recommended: {recommended}")
        else:
            typer.echo(
                f"  -> no single recommendation: {len(front)} candidate(s) on the "
                f"pareto front, a real trade-off rather than a clear winner"
            )
