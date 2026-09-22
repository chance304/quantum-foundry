"""Real device-characteristic extraction from a simulated I-V curve --
pure functions, no `kwant`/`devsim` import, so this is testable in the
lightweight CI job even though it exists to serve the real backends.

Added 2026-07-22 closing a real gap the standards audit flagged: neither
transport backend extracted V_th from a curve (it was always a fixed input
param), and nothing swept V_ds, so DIBL was structurally uncomputable.
"""
from __future__ import annotations

import itertools
import math

# Standard constant-current V_th criterion: I_d = criterion_A_per_um * (W/L),
# a widely-used industry convention (avoids the ambiguity of a purely
# geometric linear-extrapolation method). See Sze & Ng, Physics of
# Semiconductor Devices -- already this project's own cited Process-TCAD
# reference (docs/STANDARDS_AUDIT.md).
DEFAULT_CRITERION_A_PER_UM = 1e-7


def extract_vth_constant_current(
    vgs_sweep: list[float],
    currents_uA_per_um: list[float],
    criterion_A_per_um: float = DEFAULT_CRITERION_A_PER_UM,
) -> float:
    """Constant-current V_th: the V_gs at which the simulated current
    crosses `criterion_A_per_um` (converted to uA/um to match this
    codebase's current units), found by linear interpolation on
    log10(current) vs. V_gs -- current vs. V_gs is exponential in the
    subthreshold region, so interpolating in log-space is the standard,
    accurate approach (not a raw linear interpolation on current itself).

    Raises ValueError if the sweep never crosses the criterion (too low or
    too high for the simulated range) -- refuses to extrapolate blindly.
    """
    if len(vgs_sweep) != len(currents_uA_per_um):
        raise ValueError("vgs_sweep and currents_uA_per_um must be the same length")
    criterion_uA_per_um = criterion_A_per_um * 1e6

    pairs = sorted(zip(vgs_sweep, currents_uA_per_um))
    for (v_lo, i_lo), (v_hi, i_hi) in itertools.pairwise(pairs):
        if i_lo <= 0 or i_hi <= 0:
            continue
        if i_lo <= criterion_uA_per_um <= i_hi:
            if i_lo == i_hi:
                return v_lo
            log_i_lo, log_i_hi = math.log10(i_lo), math.log10(i_hi)
            log_criterion = math.log10(criterion_uA_per_um)
            frac = (log_criterion - log_i_lo) / (log_i_hi - log_i_lo)
            return v_lo + frac * (v_hi - v_lo)

    raise ValueError(
        f"Simulated current never crosses the constant-current criterion "
        f"({criterion_uA_per_um:.3g} uA/um) within the swept V_gs range "
        f"{vgs_sweep} -- cannot extract V_th, refusing to extrapolate."
    )


def compute_dibl_mV_per_V(
    vth_low_vds_V: float,
    vth_high_vds_V: float,
    vds_low_V: float,
    vds_high_V: float,
) -> float:
    """DIBL = -(V_th(high V_ds) - V_th(low V_ds)) / (V_ds_high - V_ds_low),
    reported in mV/V -- the standard definition (Sze & Ng; already this
    project's own cited Process-TCAD reference). Positive DIBL means V_th
    rolls off as V_ds increases, the expected short-channel direction.
    """
    if vds_high_V == vds_low_V:
        raise ValueError("vds_high_V and vds_low_V must differ to compute DIBL")
    return -(vth_high_vds_V - vth_low_vds_V) / (vds_high_V - vds_low_V) * 1000.0
