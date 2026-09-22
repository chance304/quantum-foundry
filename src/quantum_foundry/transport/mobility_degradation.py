"""Defect-density -> mobility degradation -- added 2026-07-22 closing a gap
the standards audit flagged: no code anywhere coupled CVD defect density
(chalcogen vacancies, grain boundaries) to a mobility correction.

Lives in transport/ (not manufacturability/) since transport is the actual
consumer -- manufacturability/ only ever imports from transport.results
today, never the reverse; putting this here avoids introducing a
layering violation while still directly serving the manufacturability
domain's own "defect density" concept.
"""
from __future__ import annotations


def matthiessens_rule_mobility(mu_a_cm2_Vs: float, mu_b_cm2_Vs: float) -> float:
    """Matthiessen's rule: independent scattering mechanisms combine as
    reciprocal rates, not the mobilities themselves --
    1/mu_total = 1/mu_a + 1/mu_b. Standard relation, see Sze & Ng, Physics
    of Semiconductor Devices (already this project's own cited
    Process-TCAD reference, docs/STANDARDS_AUDIT.md).
    """
    if mu_a_cm2_Vs <= 0 or mu_b_cm2_Vs <= 0:
        raise ValueError("mobilities must be positive")
    return 1.0 / (1.0 / mu_a_cm2_Vs + 1.0 / mu_b_cm2_Vs)


def defect_limited_mobility(defect_density_per_cm2: float, scattering_coefficient_per_Vs: float) -> float:
    """mu_defect = scattering_coefficient / defect_density -- the standard
    inverse-density functional form used for defect/impurity-limited
    scattering (same shape as ionized-impurity scattering, Sze & Ng).

    Units (found mismatched 2026-07-31 during a literature search for a
    real citable coefficient -- renamed here, not just re-documented):
    mu_defect is cm^2/(V*s), defect_density_per_cm2 is cm^-2, so
    scattering_coefficient = mu_defect * defect_density_per_cm2 has units
    cm^2/(V*s) * cm^-2 = (V*s)^-1 -- NOT cm^2, which is what the parameter
    was previously named after (scattering_coefficient_cm2). No literature
    value had been sourced yet when that name was chosen, so the mismatch
    went uncaught until an actual candidate value's units were checked.

    scattering_coefficient_per_Vs MUST be a caller-supplied, cited
    literature value -- never invented here, same discipline as
    poisson_murphy.py's defect_density_per_cm2 and its Stapper
    clustering_parameter_alpha. As of 2026-07-31: no single clean
    real-literature value exists yet for monolayer MoS2 specifically (two
    real (density, mobility) points found in Zhang et al. 2024, Adv. Sci.
    11(42) e2408640, but they're confounded by a doping difference between
    samples and don't fit one constant to within 2x) -- see
    docs/DECISIONS.md 2026-07-31 for the full literature-search writeup,
    including a real but differently-scoped WSe2 value (Wu et al. 2016,
    Nano Research, calibrated to that paper's own e-beam irradiation dose
    as a defect-density proxy, not a portable universal constant).
    """
    if defect_density_per_cm2 < 0:
        raise ValueError("defect_density_per_cm2 must be non-negative")
    if defect_density_per_cm2 == 0:
        return float("inf")  # no defects -> Matthiessen's rule falls back to the phonon-limited term alone
    if scattering_coefficient_per_Vs <= 0:
        raise ValueError("scattering_coefficient_per_Vs must be positive")
    return scattering_coefficient_per_Vs / defect_density_per_cm2
