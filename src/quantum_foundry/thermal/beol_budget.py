"""Hard-stop thermal-budget checks -- added 2026-07-22 closing a gap the
standards audit flagged: nothing anywhere enforced BEOL's or M3D
layer-transfer's processing-temperature limits.

Citations upgraded 2026-07-27 (standards audit re-pass covering everything
built since the 2026-07-21 audit):

- BEOL_MAX_TEMP_C: medium-high confidence, real reference class (not one
  clause) -- the 400-450C copper/low-k damascene thermal-budget ceiling is
  well-established across CEA-Leti's sequential-3D-integration body of work
  (e.g. P. Batude et al.'s CoolCube(TM)-program publications on thermal-
  budget-constrained 3D sequential integration; T>500C is independently
  reported to degrade already-fabricated bottom-tier transistors). No
  single clause pinned down this session -- if this project ever needs to
  defend 400C against a specific fab's own qualified BEOL spec, that still
  needs a named source, not this general reference class.
- M3D_LAYER_TRANSFER_MAX_TEMP_C: high confidence, directly verified
  (arXiv/PMC full text read, not a search-summary sentence) against a
  real, materially-relevant paper: Xie, Jia, Nie et al., "Monolithic 3D
  integration of 2D transistors and vertical RRAMs in 1T-4R structure for
  high-density memory," Nature Communications 14, 5952 (2023),
  doi:10.1038/s41467-023-41736-2 -- a monolithic 3D stack of MoS2
  transistors (this project's own anchor n-type channel material) and
  HfOx VRRAMs, which states "the highest temperature among all the
  processes being the PECVD isolation oxide growth at 300C." This is a
  real, MoS2-specific, directly-matching precedent for this project's
  300C M3D constant -- not just an analogous industry figure.
"""
from __future__ import annotations

from dataclasses import dataclass

BEOL_MAX_TEMP_C = 400.0
M3D_LAYER_TRANSFER_MAX_TEMP_C = 300.0  # Xie et al., Nat. Commun. 14, 5952 (2023) -- see module docstring


@dataclass(frozen=True)
class ThermalBudgetCheck:
    passed: bool
    limit_name: str
    limit_C: float
    actual_C: float
    margin_C: float  # limit - actual; negative means over budget


def _check(max_junction_temp_C: float, limit_name: str, limit_C: float) -> ThermalBudgetCheck:
    margin = limit_C - max_junction_temp_C
    return ThermalBudgetCheck(
        passed=margin >= 0,
        limit_name=limit_name,
        limit_C=limit_C,
        actual_C=max_junction_temp_C,
        margin_C=margin,
    )


def check_beol_budget(max_junction_temp_C: float) -> ThermalBudgetCheck:
    return _check(max_junction_temp_C, "BEOL Cu/low-k thermal budget", BEOL_MAX_TEMP_C)


def check_m3d_layer_transfer_budget(max_junction_temp_C: float) -> ThermalBudgetCheck:
    return _check(max_junction_temp_C, "M3D layer-transfer thermal budget", M3D_LAYER_TRANSFER_MAX_TEMP_C)
