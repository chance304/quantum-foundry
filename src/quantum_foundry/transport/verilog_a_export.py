"""Real Verilog-A compact-model export -- M7 (docs/ROADMAP.md), added 2026-07-22.

Scope decision, made explicitly: a real BSIM-CMG parameter fit needs
converged, multi-bias I-V data from a real DD/NEGF solver -- fitting one
against stub-level or sparse-Kwant-toy-geometry physics would be
scientifically meaningless (already flagged as blocked in the standards
audit). What's real and buildable now: a behavioral, lookup-table
(piecewise-linear) Verilog-A model encoding whatever `TransportResult.iv_curve`
a backend actually produced -- a real, standard EDA technique for early PDK
exploration, not a claim of a physically-parameterized compact model.

Written in portable IEEE 1364.1 Verilog-A -- deliberately NOT using
Spectre's `$table_model()` system function (simulator-specific), just plain
conditional arithmetic in an `analog` block, which compiles under any
standards-compliant Verilog-A parser. NOT independently verified against a
real installed SPICE/Verilog-A compiler in this session (none is available
here) -- treat the output as syntactically standards-compliant, not
simulator-verified, same honesty discipline as this project's other
"not independently verified against a real install" notes (see jarvis_dft.py).

Real gap found and fixed (2026-07-27 standards audit): the original version
of this module made I(d,s) a function of V(g,s) alone, with NO V(d,s)
dependence at all -- meaning the model would output a fixed nonzero drain
current even at V(d,s)=0, violating a basic requirement any two-terminal-
like device model must satisfy (I->0 as Vds->0, both on physical grounds --
no potential difference, no driven current -- and on SPICE numerical-
convergence grounds -- a Vds-independent current source has zero output
conductance everywhere, which is a known source of DC operating-point
non-convergence). Fixed by multiplying the looked-up (Vgs-only) current by
`tanh(V(d,s)/VDS_SAFETY_V)`: a standard smoothing-function technique (the
same category BSIM-class models use for region-transition smoothing), not
a new physical parameter -- VDS_SAFETY_V is a small numerical-safety
constant, not a fitted device quantity. tanh is odd, so this also gives the
model correct sign behavior under Vds reversal for free. At the real bias
point the model was extracted at (vds_V, typically 0.05-0.8V in this
project's backends), tanh(vds_V/VDS_SAFETY_V) > 0.999, so the perturbation
to the originally-intended I(vds_V) is negligible -- this fixes the Vds=0
pathology without changing the model's real, intended operating point.
Still NOT a triode-region physical model -- deliberately no attempt to
model the real triode/saturation transition (that would need a Vdsat this
project doesn't have and would re-introduce exactly the "fitting a
physically-parameterized model against under-resolved data" problem this
module's own scope decision above already rejected).
"""
from __future__ import annotations

import re

from .results import TransportResult

_UA_PER_UM_TO_A = 1e-6  # uA -> A; still needs *width_um to become absolute current

# Numerical-safety constant, NOT a physical/fitted device parameter -- sets
# how quickly the tanh(Vds/VDS_SAFETY_V) smoothing factor (see module
# docstring) rises from 0 at Vds=0 towards 1. 10mV is small relative to
# every vds_V this project's backends actually use (0.05-0.8V), so
# tanh(vds_V/VDS_SAFETY_V) > 0.999 at the real bias point -- negligible
# perturbation there, while fixing the Vds=0 non-physicality.
_VDS_SAFETY_V = 0.01


def _sanitize_identifier(material_id: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", material_id)
    if not sanitized or sanitized[0].isdigit():
        sanitized = f"m_{sanitized}"
    return sanitized


def export_verilog_a(material_id: str, transport_result: TransportResult, vds_V: float) -> str:
    """Behavioral (piecewise-linear lookup-table) Verilog-A module encoding
    `transport_result.iv_curve` for one real, concretely-sized device
    (channel width taken from `transport_result.device_geometry`).

    `vds_V` is the bias point the caller ran the transport backend at --
    TransportResult doesn't store this itself, and the caller already knows
    it (they passed it to the backend), so it's supplied explicitly rather
    than guessed.
    """
    points = sorted(transport_result.iv_curve)
    if len(points) < 2:
        raise ValueError(
            f"Need at least 2 iv_curve points to build a piecewise-linear "
            f"Verilog-A model, got {len(points)}."
        )

    width_um = transport_result.device_geometry.channel_width_nm / 1000.0
    module_name = f"qf_{_sanitize_identifier(material_id)}_behavioral"
    backend_kind = "stub (illustrative, not ab-initio/NEGF-verified)" if transport_result.provenance.is_stub else "real solver"

    amps = [i_uA_per_um * width_um * _UA_PER_UM_TO_A for _vgs, i_uA_per_um in points]
    vgs = [v for v, _i in points]

    lines = [
        "// Behavioral (piecewise-linear lookup-table) Verilog-A compact model.",
        "// NOT a physically-parameterized BSIM-CMG fit -- encodes a real",
        f"// simulated I(Vgs) curve for '{material_id}' at Vds={vds_V}V, produced",
        f"// by a {backend_kind} transport backend, for a device with",
        f"// channel_width_nm={transport_result.device_geometry.channel_width_nm}.",
        "// Written in portable IEEE 1364.1 Verilog-A (no simulator-specific",
        "// system functions). NOT independently verified against a real",
        "// installed SPICE/Verilog-A compiler in this session -- treat as",
        "// syntactically standards-compliant, not simulator-verified.",
        "// See docs/DECISIONS.md 2026-07-22 for the full scope decision.",
        "// I(d,s) is scaled by tanh(V(d,s)/VDS_SAFETY_V) -- a numerical-",
        "// safety smoothing factor (NOT a fitted device parameter) fixing a",
        "// real gap found 2026-07-27: without it, I(d,s) was independent of",
        "// V(d,s) entirely, so the model wrongly output a fixed nonzero",
        "// current even at Vds=0. See this file's own docstring for the full story.",
        "",
        '`include "constants.vams"',
        '`include "disciplines.vams"',
        "",
        f"module {module_name}(d, g, s);",
        "    inout d, g, s;",
        "    electrical d, g, s;",
        "    real i_lookup;",
        "",
        "    analog begin",
        "        I(g,s) <+ 0;  // ideal open-gate DC behavior",
    ]

    for i, (v, amp) in enumerate(zip(vgs, amps)):
        if i == 0:
            lines.append(f"        if (V(g,s) <= {v}) begin")
            lines.append(f"            i_lookup = {amp};")
            lines.append("        end")
        else:
            v_prev, amp_prev = vgs[i - 1], amps[i - 1]
            lines.append(f"        else if (V(g,s) <= {v}) begin")
            lines.append(
                f"            i_lookup = {amp_prev} + ({amp} - {amp_prev}) "
                f"* (V(g,s) - {v_prev}) / ({v} - {v_prev});"
            )
            lines.append("        end")

    lines.append("        else begin")
    lines.append(f"            i_lookup = {amps[-1]};  // clamp beyond the simulated Vgs range")
    lines.append("        end")
    lines.append(f"        I(d,s) <+ i_lookup * tanh(V(d,s) / {_VDS_SAFETY_V});")
    lines.append("    end")
    lines.append("endmodule")

    return "\n".join(lines) + "\n"
