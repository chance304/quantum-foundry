"""Functional-transistor criterion -- added 2026-07-22 closing a gap the
standards audit flagged: no yield model anywhere accounted for whether a
die's transistor actually switches, only whether it's defect-free.

FUNCTIONAL_ION_IOFF_RATIO_MIN is a widely-cited minimum on/off ratio for a
functional logic transistor (see e.g. IRDS/ITRS-class device roadmaps) --
flagged as a common engineering threshold, not one single official clause
citation, matching this project's confidence-flagging habit
(docs/STANDARDS_AUDIT.md).
"""
from __future__ import annotations

FUNCTIONAL_ION_IOFF_RATIO_MIN = 1e5


def is_functional_transistor(
    ion_uA_per_um: float,
    ioff_uA_per_um: float,
    min_ratio: float = FUNCTIONAL_ION_IOFF_RATIO_MIN,
) -> bool:
    if ioff_uA_per_um <= 0:
        # Zero (or negative/unphysical) off-current trivially satisfies any
        # finite ratio requirement -- avoid a ZeroDivisionError rather than
        # special-casing the caller.
        return True
    return (ion_uA_per_um / ioff_uA_per_um) >= min_ratio
