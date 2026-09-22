"""Stub manufacturability backend: trivial linear defect_density*area, not
even a Poisson shape — deliberately the crudest possible model, since the
REAL closed-form Poisson/Murphy model is Phase-1 REAL scope already
(manufacturability/poisson_murphy.py), not deferred.
"""
from __future__ import annotations

from ..provenance import ProvenanceInfo
from ..transport.results import TransportResult
from .results import YieldResult

STUB_TOOL_VERSION = "trivial-linear-stub-0.1"
_DEFAULT_DEFECT_DENSITY_PER_CM2 = 1.0  # arbitrary, uncited — stub only


def run(transport_result: TransportResult, params: dict) -> YieldResult:
    d0_was_defaulted = "defect_density_per_cm2" not in params
    defect_density = params.get("defect_density_per_cm2", _DEFAULT_DEFECT_DENSITY_PER_CM2)
    geom = transport_result.device_geometry
    area_um2 = geom.channel_width_nm * geom.channel_length_nm * 1e-6
    yield_fraction = max(0.0, 1.0 - defect_density * (area_um2 * 1e-8))

    return YieldResult(
        yield_fraction=yield_fraction,
        defect_density_per_cm2=defect_density,
        critical_area_um2=area_um2,
        model="trivial_linear",
        confidence_interval=None,
        provenance=ProvenanceInfo(
            backend_name="manufacturability_stub_trivial", is_stub=True, tool_version=STUB_TOOL_VERSION
        ),
        extra={"defect_density_defaulted_uncited": d0_was_defaulted},
    )


class TrivialYieldStub:
    name = "stub"
    is_stub = True

    def run(self, transport_result, params):
        return run(transport_result, params)
