"""Real HotSpot backend: shells out to the vendored binary
(.vendor/hotspot/hotspot, built by scripts/setup_env.sh) using HotSpot's
multi-layer grid model (-model_type grid -detailed_3D on, a per-layer .flp
floorplan + a stack .lcf layer-config file) — not the default single
lumped-node block model — to represent the actual channel/gate-oxide/
substrate stack.

VERIFIED 2026-07-21 against a real built HotSpot binary (cloned from
github.com/uvahotspot/HotSpot, `make` succeeded cleanly) and a real minimal
2-layer steady-state grid run. This caught and fixed two real format bugs
the first version of this module had (both from guessing, not verifying):

1. The .flp column order is `<Unit> <Width> <Height> <X> <Y>` (all meters) —
   NOT `<Unit> <X> <Y> <Width> <Height>` as originally written.
2. The .lcf format is a 7-line block per layer (layer number; lateral heat
   flow Y/N; power dissipation Y/N; specific heat capacity in J/(m^3*K);
   resistivity in (m*K)/W -- the RECIPROCAL of thermal conductivity, not
   thermal conductivity itself; thickness in meters; floorplan filename),
   blank-line separated -- NOT one tab-separated line per layer.

Also found by running the real binary, not documented anywhere obvious:
HotSpot's grid model requires -grid_rows/-grid_cols to be powers of two
(the shipped template.config's default of 39 is NOT and errors out); both
-grid_steady_file and -steady_file must be passed together.

Updated 2026-07-22: `materials/schema.py`'s MaterialRecord now has a
`specific_heat_capacity_J_per_m3K` field, but no seeded material has a real
value yet -- this backend still falls back to an uncited generic default
(_DEFAULT_SPECIFIC_HEAT_J_M3K, matching the value HotSpot's own examples use
for silicon) per layer without one, now flagged the same way as the
existing thermal-conductivity fallback (`extra["specific_heat_fallback_used_for"]`,
a real per-layer list) rather than the previous hardcoded blanket flag.

A second real issue, found and FIXED (not just documented) after the first
version of this module was published: running the actual 20nm x 100nm CLI-
default device geometry as if it WERE the entire floorplan didn't complete
in any reasonable time, even though a manual 10um-scale test of the exact
same file formats completed in seconds. Bisecting device size (1um: still
slow; 100um: fast) found the real cause -- HotSpot's grid model is designed
for chip-level floorplans (mm-scale dies with many functional blocks), and
its default package/heatsink parameters (`s_sink`/`s_spreader` in
hotspot.config, centimeter-scale) create a numerically extreme scale
mismatch when the "floorplan" IS the bare nm-scale device with nothing
else in it. The fix: `_pad_to_die_footprint()` places the real device as
one named block inside a synthetic `_MIN_DIE_SIDE_M`-sized die footprint,
with the remaining area filled by two unpowered "die_fill" blocks (same
layer material, just context) -- this is not just a numerical trick, it's
also more physically honest: a real transistor is never thermally isolated
in a cm-scale package, it sits inside a realistically-sized chip. The
`extra["synthetic_die_padding_applied"]` field on the result says plainly
when this padding was used, so it's never mistaken for the device's real
footprint.

Requires: scripts/setup_env.sh already run (vendors the binary + config).

No interfacial (Kapitza) thermal resistance term (flagged 2026-07-21
standards audit, docs/STANDARDS_AUDIT.md): each .lcf layer only carries a
bulk resistivity (1/thermal_conductivity_W_mK); there is no per-interface
term at all. For a 2D-material device, interface resistance (e.g.
MoS2/SiO2) is frequently the *dominant* thermal-resistance term, not a
second-order correction -- every max_junction_temp_C this backend produces
is a likely underestimate until a real Kapitza value is sourced and added
(planned for the M5 FEniCSx path, not this backend -- see docs/M5_PLAN.md).
Flagged explicitly via extra["kapitza_resistance_included"] = False below,
same honesty pattern as the existing specific-heat/thermal-conductivity
fallback flags.

M9b (2026-07-27, docs/M9_PLAN.md) added `run_stacked()`/
`default_stacked_stack_from_geometry()` for real multi-tier (CFET/M3D)
thermal modeling -- see their docstrings below. This DOES model an
inter-tier Kapitza interface (unlike the single-tier `run()` path above,
which still has none): each `default_stacked_stack_from_geometry()`-built
stack gets a synthetic `"tier_interface"`-role layer between every adjacent
pair of stacked channels, using the exact `k_eff = t_thin / R_Kapitza`
technique `docs/M5_PLAN.md`'s "Interfacial (Kapitza) thermal resistance"
section already designed for the MoS2/SiO2 substrate interface -- reused,
not reinvented. Still needs a real, citable `R_Kapitza` for whatever
bonding/layer-transfer interface is actually used -- `run_stacked()` refuses
to run without a caller-supplied `kapitza_resistance_m2K_per_W`, same
never-invent-it discipline as `manufacturability/poisson_murphy.py`'s D0/
alpha params.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from ..provenance import ProvenanceInfo
from ..transport.results import DeviceGeometry, TransportResult
from .results import FieldHandle, MaterialStack, ThermalLayer, ThermalResult

HOTSPOT_BIN = Path(__file__).parents[3] / ".vendor" / "hotspot" / "hotspot"
HOTSPOT_CONFIG = Path(__file__).parents[3] / ".vendor" / "hotspot" / "hotspot.config"

# HotSpot's grid model requires powers of two -- verified 2026-07-21 (the
# shipped template.config's default of 39x39 is rejected outright). 16 is
# the resolution actually verified fast (~seconds) in this session; this
# build has no SuperLU (-DSUPERLU=0, see docker/README.md-equivalent build
# notes) so its solver is comparatively slow -- 64 was tried and took much
# longer than this session's time budget allowed to confirm completion.
# Raise this once a faster solver (SuperLU) is confirmed available, or once
# verified acceptable on the real self-hosted runner.
_DEFAULT_GRID_ROWS = 16
_DEFAULT_GRID_COLS = 16

# MaterialRecord.specific_heat_capacity_J_per_m3K exists (added 2026-07-22)
# but no seeded material has a real value yet -- this generic default
# matches what HotSpot's own bundled examples use for silicon layers, used
# per-layer only when that material's real field is None. Flagged in
# `extra["specific_heat_fallback_used_for"]` on every ThermalResult this
# backend produces, never presented as material-specific.
_DEFAULT_SPECIFIC_HEAT_J_M3K = 1.75e6

# Real, measured threshold (bisected 2026-07-21): 1um-scale floorplans did
# not complete in 25s against this build's solver; 100um did, quickly. This
# is the minimum synthetic die footprint _pad_to_die_footprint() pads any
# smaller device up to -- see module docstring for the physical reasoning,
# not just the numerical one.
_MIN_DIE_SIDE_M = 1e-4  # 100um

# Matches thermal/stub.py's own default substrate thickness constant exactly
# (not re-derived) -- both model the same "300um default Si wafer" simplification.
_DEFAULT_SUBSTRATE_THICKNESS_NM = 300_000.0


def _pad_to_die_footprint(unit_name: str, width_m: float, length_m: float, fill_unit_name: str):
    """Returns a list of (name, width, height, x, y) tuples tiling a
    _MIN_DIE_SIDE_M x _MIN_DIE_SIDE_M square: the real device block plus up
    to two unpowered filler blocks covering the rest, with no gaps or
    overlaps. Returns just the device block, unpadded, if it's already >=
    the minimum die side (padding would be a no-op or shrink it)."""
    if width_m >= _MIN_DIE_SIDE_M or length_m >= _MIN_DIE_SIDE_M:
        return [(unit_name, width_m, length_m, 0.0, 0.0)], False

    blocks = [(unit_name, width_m, length_m, 0.0, 0.0)]
    right_w = _MIN_DIE_SIDE_M - width_m
    if right_w > 0:
        blocks.append((f"{fill_unit_name}_right", right_w, length_m, width_m, 0.0))
    top_h = _MIN_DIE_SIDE_M - length_m
    if top_h > 0:
        blocks.append((f"{fill_unit_name}_top", _MIN_DIE_SIDE_M, top_h, 0.0, length_m))
    return blocks, True


def _write_layer_files(
    tmpdir: Path,
    stack: MaterialStack,
    transport_results: list[TransportResult],
    materials_db,
    params: dict | None = None,
):
    """Writes the .flp/.lcf/.ptrace files for one HotSpot run.

    `transport_results` is matched 1:1, in stack order, to the stack's
    "channel"-role layers -- one real `TransportResult` per stacked tier
    (M9b, 2026-07-27; the single-tier case is just `[transport_result]`,
    unchanged behavior from before this list-based signature). Real
    assumption, stated plainly: every tier shares the same
    channel_length_nm/channel_width_nm footprint -- true by construction
    for a real CFET (that's the point: same gate footprint, stacked), and
    this is what makes a single shared width_m/length_m below correct
    rather than an oversimplification.

    A "tier_interface"-role layer (`default_stacked_stack_from_geometry()`
    below) does NOT get a materials_db lookup -- there's no real material
    there, it's a synthetic Kapitza-resistance stand-in. Its resistivity is
    computed directly from a caller-supplied `params["kapitza_resistance_m2K_per_W"]`
    (`k_eff = t_thin / R_Kapitza`, i.e. resistivity = R_Kapitza / t_thin) --
    refuses to run without it, same never-invent-a-constant discipline as
    `manufacturability/poisson_murphy.py`'s defect_density_per_cm2.
    """
    params = params or {}
    channel_layer_indices = [i for i, layer in enumerate(stack.layers) if layer.role == "channel"]
    if len(channel_layer_indices) != len(transport_results):
        raise ValueError(
            f"Got {len(transport_results)} transport result(s) but the stack has "
            f"{len(channel_layer_indices)} 'channel'-role layer(s) -- these must "
            f"match 1:1, one real TransportResult per stacked tier (docs/M9_PLAN.md M9b)."
        )
    power_by_index: dict[int, float] = {}
    for idx, tr in zip(channel_layer_indices, transport_results):
        geom = tr.device_geometry
        power_by_index[idx] = tr.power_density_W_per_um2 * (geom.channel_width_nm * geom.channel_length_nm * 1e-6)

    geom0 = transport_results[0].device_geometry
    width_m = geom0.channel_width_nm * 1e-9
    length_m = geom0.channel_length_nm * 1e-9

    kapitza_r = params.get("kapitza_resistance_m2K_per_W")
    has_interface_layers = any(layer.role == "tier_interface" for layer in stack.layers)
    if has_interface_layers and kapitza_r is None:
        raise ValueError(
            "Stack has a 'tier_interface' layer but params['kapitza_resistance_m2K_per_W'] "
            "was not supplied -- refusing to invent an inter-tier thermal-resistance value. "
            "Source a real, citable value first (see docs/ROADMAP.md)."
        )

    lcf_lines: list[str] = []
    ptrace_units: list[str] = []
    ptrace_powers: list[str] = []
    k_fallback_used: list[str] = []
    c_fallback_used: list[str] = []
    padding_applied = False

    for i, layer in enumerate(stack.layers):
        # Unique per layer (not just layer.role) -- a stacked stack can have
        # more than one "channel"-role layer, and HotSpot's unit names must
        # be unique across the whole floorplan.
        unit_name = f"{layer.role}_{i}"
        flp_path = tmpdir / f"layer_{i}.flp"
        blocks, was_padded = _pad_to_die_footprint(unit_name, width_m, length_m, f"{unit_name}_fill")
        padding_applied = padding_applied or was_padded
        # Real .flp column order: Unit, Width, Height, X, Y (all meters) --
        # verified against HotSpot's own example .flp files.
        flp_path.write_text(
            "".join(f"{name}\t{w:.6e}\t{h:.6e}\t{x:.6e}\t{y:.6e}\n" for name, w, h, x, y in blocks)
        )

        c: float | None
        if layer.role == "tier_interface":
            # Synthetic Kapitza stand-in -- no real material, never looked
            # up in materials_db (see docstring above).
            assert kapitza_r is not None  # guaranteed by the has_interface_layers check above
            resistivity = kapitza_r / (layer.thickness_nm * 1e-9)
            c = _DEFAULT_SPECIFIC_HEAT_J_M3K
            c_fallback_used.append(layer.material_id)
        else:
            material = materials_db.get(layer.material_id) if layer.material_id in materials_db else None
            k = material.thermal_conductivity_W_mK if material else None
            if k is None:
                resistivity = 1.0 / 100.0  # silicon-order-of-magnitude fallback, NOT a citation
                k_fallback_used.append(layer.material_id)
            else:
                resistivity = 1.0 / k

            c = material.specific_heat_capacity_J_per_m3K if material else None
            if c is None:
                c = _DEFAULT_SPECIFIC_HEAT_J_M3K
                c_fallback_used.append(layer.material_id)

        is_powered = layer.role == "channel"  # only channel layers dissipate power in this model
        lcf_lines.append(
            f"{i}\nY\n{'Y' if is_powered else 'N'}\n"
            f"{c:.4e}\n{resistivity:.6e}\n"
            f"{layer.thickness_nm * 1e-9:.6e}\n{flp_path}\n"
        )
        # Real, verified requirement (found 2026-07-21, two iterations
        # against the actual binary's error messages -- first attempt
        # included every layer's units and got "no. of units in floorplan
        # and trace file differ" again; checking HotSpot's own example4
        # ptrace against its per-layer .flp files showed only layers marked
        # power-dissipating "Y" contribute ANY units to the ptrace header --
        # non-powered layers (e.g. TIM interface layers) are entirely
        # absent from it, not zero-valued): only add ptrace entries for
        # units belonging to a power="Y" layer; within that layer, the real
        # device gets its real power, fill blocks get an explicit 0.0.
        if is_powered:
            power_w = power_by_index[i]
            for name, *_rest in blocks:
                ptrace_units.append(name)
                ptrace_powers.append(f"{power_w:.6e}" if name == unit_name else "0.0")

    lcf_path = tmpdir / "device.lcf"
    lcf_path.write_text("\n".join(lcf_lines))

    ptrace_path = tmpdir / "device.ptrace"
    ptrace_path.write_text("\t".join(ptrace_units) + "\n" + "\t".join(ptrace_powers) + "\n")

    return lcf_path, ptrace_path, k_fallback_used, c_fallback_used, padding_applied


def _parse_max_temp_kelvin(steady_output: str) -> float:
    max_k = 0.0
    for line in steady_output.splitlines():
        parts = line.split()
        if len(parts) == 2:
            try:
                max_k = max(max_k, float(parts[1]))
            except ValueError:
                continue
    return max_k if max_k else float("nan")


def _require_hotspot_binary() -> None:
    if not HOTSPOT_BIN.exists():
        raise RuntimeError(
            f"HotSpot not found at {HOTSPOT_BIN} — run scripts/setup_env.sh "
            f"or scripts/preflight.sh to see what's missing."
        )
    if not HOTSPOT_CONFIG.exists():
        raise RuntimeError(
            f"HotSpot config not found at {HOTSPOT_CONFIG} — scripts/setup_env.sh "
            f"should vendor HotSpot's template.config as hotspot.config alongside "
            f"the binary."
        )


def _invoke_hotspot(lcf_path: Path, ptrace_path: Path, tmpdir: Path, params: dict) -> tuple[float, str]:
    """Runs the real HotSpot binary against already-written layer files,
    returns max junction temp in Kelvin. Shared by run() and run_stacked() --
    everything above this point (layer-file writing) differs between the two,
    everything from here down (invoking the binary, parsing its output) does
    not."""
    steady_file = tmpdir / "device.steady"
    grid_steady_file = tmpdir / "grid.steady"

    cmd = [
        str(HOTSPOT_BIN),
        "-c", str(HOTSPOT_CONFIG),
        "-p", str(ptrace_path),
        "-grid_layer_file", str(lcf_path),
        "-model_type", "grid",
        "-detailed_3D", "on",
        "-grid_rows", str(params.get("grid_rows", _DEFAULT_GRID_ROWS)),
        "-grid_cols", str(params.get("grid_cols", _DEFAULT_GRID_COLS)),
        "-steady_file", str(steady_file),
        "-grid_steady_file", str(grid_steady_file),
    ]
    # check=False: the return code is inspected explicitly below (raising a
    # RuntimeError with HotSpot's captured stdout/stderr on failure), rather
    # than letting subprocess.run raise CalledProcessError -- so the default
    # check=False is intentional, not an oversight.
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=tmpdir, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"HotSpot exited {proc.returncode}: {proc.stdout[-2000:]}{proc.stderr[-2000:]}")

    steady_text = steady_file.read_text()
    return _parse_max_temp_kelvin(steady_text), steady_text


def run(transport_result: TransportResult, stack: MaterialStack, params: dict) -> ThermalResult:
    _require_hotspot_binary()

    from ..materials.registry import MaterialsDB

    materials_db = params.get("materials_db") or MaterialsDB()

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        lcf_path, ptrace_path, k_fallback_used, c_fallback_used, padding_applied = _write_layer_files(
            tmpdir, stack, [transport_result], materials_db, params
        )
        max_temp_k, steady_text = _invoke_hotspot(lcf_path, ptrace_path, tmpdir, params)

    max_temp_c = max_temp_k - 273.15
    ambient_c = params.get("ambient_temp_C", 45.0)  # HotSpot's default ambient is 318.15K = 45C, not 25C
    power_w = transport_result.power_density_W_per_um2 * (
        transport_result.device_geometry.channel_width_nm
        * transport_result.device_geometry.channel_length_nm
        * 1e-6
    )

    return ThermalResult(
        max_junction_temp_C=max_temp_c,
        thermal_resistance_K_per_W=(max_temp_c - ambient_c) / power_w if power_w else float("nan"),
        stress_MPa=None,  # thermal-only; mechanical stress needs Elmer (M5)
        field_handle=FieldHandle(format="hotspot_grid_steady", path=None, loader=lambda: steady_text),
        provenance=ProvenanceInfo(backend_name="hotspot", is_stub=False, tool_version="hotspot-verified-2026-07-21"),
        extra={
            "layers": [layer.role for layer in stack.layers],
            "specific_heat_fallback_used_for": c_fallback_used,
            "thermal_conductivity_fallback_used_for": k_fallback_used,
            "synthetic_die_padding_applied": padding_applied,
            "kapitza_resistance_included": False,
        },
    )


def default_stacked_stack_from_geometry(
    geometry: DeviceGeometry, interface_thickness_nm: float = 1.0
) -> MaterialStack:
    """M9b (2026-07-27, docs/M9_PLAN.md): builds a MaterialStack for a
    stacked/folded device (CFET/M3D) from DeviceGeometry.stacked_tiers --
    one "channel"-role ThermalLayer per DeviceTier (in stack order, e.g. a
    CFET's n-tier then p-tier), with a synthetic "tier_interface"-role
    ThermalLayer between every adjacent pair. Interface layers carry no real
    material_id -- run_stacked()/`_write_layer_files()` never look them up
    in materials_db, they compute a resistivity directly from a caller-
    supplied kapitza_resistance_m2K_per_W instead (see that function's
    docstring). Mirrors default_stack_from_geometry()'s existing gate_oxide/
    substrate wrapping exactly -- additive, not a fork of it.
    """
    tiers = geometry.stacked_tiers
    if not tiers:
        raise ValueError(
            "default_stacked_stack_from_geometry() requires DeviceGeometry.stacked_tiers "
            "to be set -- use default_stack_from_geometry() for a single-tier device."
        )
    layers: list[ThermalLayer] = []
    for i, tier in enumerate(tiers):
        if i > 0:
            layers.append(ThermalLayer(f"kapitza_interface_{i}", interface_thickness_nm, "tier_interface"))
        layers.append(ThermalLayer(tier.channel_material_id, tier.channel_thickness_nm, "channel"))
    layers.append(ThermalLayer(geometry.gate_oxide_material_id, geometry.gate_oxide_thickness_nm, "gate_oxide"))
    if geometry.substrate_material_id:
        layers.append(
            ThermalLayer(geometry.substrate_material_id, _DEFAULT_SUBSTRATE_THICKNESS_NM, "substrate")
        )
    return MaterialStack(layers=layers)


def run_stacked(transport_results: list[TransportResult], stack: MaterialStack, params: dict) -> ThermalResult:
    """M9b (2026-07-27, docs/M9_PLAN.md): real multi-tier (CFET/M3D) compact
    thermal model. Each stacked tier gets its own real power (from its own
    TransportResult, matched 1:1 in stack order to the stack's "channel"-role
    layers) instead of one tier's power being silently applied to every
    channel layer -- the bug found while scoping M9. Total dissipated power
    (for thermal_resistance_K_per_W) is the real sum across every tier, since
    they're all part of the same physical stack dissipating heat into the
    same package.

    Requires params["kapitza_resistance_m2K_per_W"] if `stack` has any
    "tier_interface" layers (real for any stack built by
    default_stacked_stack_from_geometry() above) -- see _write_layer_files()'s
    docstring for why this is never invented.
    """
    _require_hotspot_binary()

    from ..materials.registry import MaterialsDB

    materials_db = params.get("materials_db") or MaterialsDB()

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        lcf_path, ptrace_path, k_fallback_used, c_fallback_used, padding_applied = _write_layer_files(
            tmpdir, stack, transport_results, materials_db, params
        )
        max_temp_k, steady_text = _invoke_hotspot(lcf_path, ptrace_path, tmpdir, params)

    max_temp_c = max_temp_k - 273.15
    ambient_c = params.get("ambient_temp_C", 45.0)
    total_power_w = sum(
        tr.power_density_W_per_um2 * (tr.device_geometry.channel_width_nm * tr.device_geometry.channel_length_nm * 1e-6)
        for tr in transport_results
    )

    return ThermalResult(
        max_junction_temp_C=max_temp_c,
        thermal_resistance_K_per_W=(max_temp_c - ambient_c) / total_power_w if total_power_w else float("nan"),
        stress_MPa=None,  # thermal-only; mechanical stress needs Elmer (M5)
        field_handle=FieldHandle(format="hotspot_grid_steady", path=None, loader=lambda: steady_text),
        provenance=ProvenanceInfo(
            backend_name="hotspot_stacked", is_stub=False, tool_version="hotspot-verified-2026-07-21"
        ),
        extra={
            "layers": [layer.role for layer in stack.layers],
            "specific_heat_fallback_used_for": c_fallback_used,
            "thermal_conductivity_fallback_used_for": k_fallback_used,
            "synthetic_die_padding_applied": padding_applied,
            "kapitza_resistance_included": any(layer.role == "tier_interface" for layer in stack.layers),
            "n_tiers": len(transport_results),
        },
    )


class HotSpotThermalBackend:
    name, is_stub = "hotspot", False

    def run(self, transport_result, stack, params):
        return run(transport_result, stack, params)
