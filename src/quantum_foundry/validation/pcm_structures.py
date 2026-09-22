"""Synthetic PCM (process control monitor) test structures -- TLM and van
der Pauw -- added 2026-07-22 closing a gap the standards audit flagged: no
code path existed from a simulated device to a calibratable measurement
structure at all.

These are SELF-CONSISTENCY testbeds, not new experimental physics: given a
KNOWN ground-truth R_c/R_sheet, forward-model what a real structure would
measure, then run the real, standard extraction algorithm and confirm it
recovers the input. This proves the extraction math is implemented
correctly -- a real, standard EDA-calibration engineering deliverable,
exactly the kind of thing that should be right before it's ever pointed at
a real wafer measurement.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

# ---------- TLM (Transmission Line Method) ----------


@dataclass(frozen=True)
class TLMExtractionResult:
    sheet_resistance_ohm_sq: float
    contact_resistance_ohm_um: float


def synthesize_tlm_measurements(
    sheet_resistance_ohm_sq: float,
    contact_resistance_ohm_um: float,
    channel_width_um: float,
    spacings_um: list[float],
) -> list[tuple[float, float]]:
    """Forward model: what a real TLM structure would measure at each
    contact spacing, given known ground-truth R_sheet/R_c. Standard model:
    R_total(L) = R_sheet*(L/W) + 2*R_c/W (R_c already width-normalized,
    matching this codebase's own contact_resistance_ohm_um convention).
    """
    return [
        (spacing, sheet_resistance_ohm_sq * (spacing / channel_width_um) + 2 * contact_resistance_ohm_um / channel_width_um)
        for spacing in spacings_um
    ]


def extract_tlm_parameters(measurements: list[tuple[float, float]], channel_width_um: float) -> TLMExtractionResult:
    """Standard TLM linear-regression extraction: R_total vs. L is linear;
    slope -> R_sheet, intercept -> R_c. Requires >= 2 distinct spacings.
    """
    if len(measurements) < 2:
        raise ValueError("TLM extraction needs at least 2 contact-spacing measurements")
    spacings = np.array([m[0] for m in measurements])
    resistances = np.array([m[1] for m in measurements])
    slope, intercept = np.polyfit(spacings, resistances, 1)
    if intercept < 0:
        raise ValueError(
            f"TLM extraction produced a negative contact-resistance intercept "
            f"({intercept:.4g}) -- physically invalid, refusing to return it as real."
        )
    return TLMExtractionResult(
        sheet_resistance_ohm_sq=float(slope * channel_width_um),
        contact_resistance_ohm_um=float(intercept * channel_width_um / 2),
    )


# ---------- van der Pauw ----------


def synthesize_van_der_pauw_measurement(sheet_resistance_ohm_sq: float, asymmetry_ratio: float = 1.0) -> tuple[float, float]:
    """Forward model: the two orthogonal resistances (R_A, R_B) a real van
    der Pauw structure would measure, given a known ground-truth sheet
    resistance. asymmetry_ratio = R_A/R_B (1.0 -> perfectly symmetric
    sample); both returned values genuinely satisfy the real van der Pauw
    relation exactly (solved via brentq), not an approximation.
    """
    if asymmetry_ratio <= 0:
        raise ValueError("asymmetry_ratio must be positive")

    def f(r_b: float) -> float:
        r_a = asymmetry_ratio * r_b
        return (
            math.exp(-math.pi * r_a / sheet_resistance_ohm_sq)
            + math.exp(-math.pi * r_b / sheet_resistance_ohm_sq)
            - 1.0
        )

    hi = 200.0 * sheet_resistance_ohm_sq / min(1.0, asymmetry_ratio)
    r_b = brentq(f, 1e-9, hi)
    return asymmetry_ratio * r_b, r_b


def extract_van_der_pauw_sheet_resistance(r_a_ohm: float, r_b_ohm: float) -> float:
    """Solves the REAL van der Pauw (1958) transcendental equation
    exp(-pi*R_A/R_s) + exp(-pi*R_B/R_s) = 1 for R_s via
    scipy.optimize.brentq -- not the simplified symmetric-sample
    approximation R_s = (pi/ln2)*(R_A+R_B)/2, which is only exact when
    R_A == R_B. van der Pauw, L.J. (1958), "A method of measuring specific
    resistivity and Hall effect of discs of arbitrary shape," Philips Res.
    Rep. 13, 1-9.
    """
    if r_a_ohm <= 0 or r_b_ohm <= 0:
        raise ValueError("r_a_ohm and r_b_ohm must be positive")

    def f(r_s: float) -> float:
        return math.exp(-math.pi * r_a_ohm / r_s) + math.exp(-math.pi * r_b_ohm / r_s) - 1.0

    hi = 1000.0 * math.pi * max(r_a_ohm, r_b_ohm)
    return brentq(f, 1e-9, hi)
