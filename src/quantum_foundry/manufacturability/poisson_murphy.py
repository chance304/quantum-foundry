"""Poisson (Y = exp(-D0*A)), Murphy (Y = ((1-exp(-D0*A))/(D0*A))^2), and
negative-binomial/Stapper (Y = (1+D0*A/alpha)^(-alpha)) closed-form yield
models — Phase-1 REAL scope per docs/ARCHITECTURE.md. Monte Carlo
defect-placement is deferred (M5+).

defect_density_per_cm2 MUST be a cited literature value supplied by the
caller — this module does not invent one. Unlike manufacturability/stub.py,
it refuses to run without it.

Negative-binomial (added 2026-07-22, docs/STANDARDS_AUDIT.md Tier 2 — C.H.
Stapper, "Modeling of Defects in Integrated Circuit Photolithographic
Patterns," IBM J. Res. Dev., 1984): Poisson/Murphy assume a fixed
(uniform, or one specific) defect-clustering shape, which real fabs know
is often wrong — real defects cluster. Stapper's model adds a clustering
parameter alpha (as alpha -> infinity, it converges to the Poisson result
— the uniform-defect limit). Like defect_density_per_cm2, alpha MUST be a
real, caller-supplied literature value — this module adds the *model*, not
a citable alpha (that's a separate, still-open docs/ROADMAP.md item; no
citable value has been sourced yet).
"""
from __future__ import annotations

import math

from ..provenance import ProvenanceInfo
from ..transport.results import TransportResult
from .results import YieldResult

TOOL_VERSION = "poisson-murphy-0.1"


def _critical_area_cm2(transport_result: TransportResult, params: dict) -> float:
    geom = transport_result.device_geometry
    device_area_um2 = geom.channel_width_nm * geom.channel_length_nm * 1e-6
    # devices_per_die is a real die-level estimate — a research task for the
    # caller to supply, not invented here.
    devices_per_die = params.get("devices_per_die", 1.0)
    return device_area_um2 * devices_per_die * 1e-8


def run_poisson(transport_result: TransportResult, defect_density_per_cm2: float, params: dict) -> YieldResult:
    area_cm2 = _critical_area_cm2(transport_result, params)
    d0a = defect_density_per_cm2 * area_cm2
    return YieldResult(
        yield_fraction=math.exp(-d0a),
        defect_density_per_cm2=defect_density_per_cm2,
        critical_area_um2=area_cm2 * 1e8,
        model="poisson",
        confidence_interval=None,
        provenance=ProvenanceInfo(backend_name="poisson_yield", is_stub=False, tool_version=TOOL_VERSION),
    )


def run_murphy(transport_result: TransportResult, defect_density_per_cm2: float, params: dict) -> YieldResult:
    area_cm2 = _critical_area_cm2(transport_result, params)
    d0a = defect_density_per_cm2 * area_cm2
    y = ((1 - math.exp(-d0a)) / d0a) ** 2 if d0a > 0 else 1.0
    return YieldResult(
        yield_fraction=y,
        defect_density_per_cm2=defect_density_per_cm2,
        critical_area_um2=area_cm2 * 1e8,
        model="murphy",
        confidence_interval=None,
        provenance=ProvenanceInfo(backend_name="murphy_yield", is_stub=False, tool_version=TOOL_VERSION),
    )


def run_negative_binomial(
    transport_result: TransportResult,
    defect_density_per_cm2: float,
    clustering_parameter_alpha: float,
    params: dict,
) -> YieldResult:
    area_cm2 = _critical_area_cm2(transport_result, params)
    d0a = defect_density_per_cm2 * area_cm2
    y = (1 + d0a / clustering_parameter_alpha) ** (-clustering_parameter_alpha)
    return YieldResult(
        yield_fraction=y,
        defect_density_per_cm2=defect_density_per_cm2,
        critical_area_um2=area_cm2 * 1e8,
        model="negative_binomial",
        confidence_interval=None,
        provenance=ProvenanceInfo(backend_name="negative_binomial_yield", is_stub=False, tool_version=TOOL_VERSION),
        extra={"clustering_parameter_alpha": clustering_parameter_alpha},
    )


def _require_d0(params: dict) -> float:
    d0 = params.get("defect_density_per_cm2")
    if d0 is None:
        raise ValueError(
            "poisson_murphy requires a cited defect_density_per_cm2 param — "
            "never defaulted for a real backend. Supply a literature value "
            "with its source (see docs/ROADMAP.md's 'Source a real, citable "
            "defect density (D0) for CVD-grown 2D-TMD films' open item)."
        )
    return d0


def _require_alpha(params: dict) -> float:
    alpha = params.get("clustering_parameter_alpha")
    if alpha is None:
        raise ValueError(
            "negative_binomial requires a cited clustering_parameter_alpha "
            "param — never defaulted. Supply a literature value with its "
            "source (see docs/ROADMAP.md's 'Source a real, citable Stapper "
            "clustering parameter (alpha) for CVD-grown 2D-TMD films' open "
            "item — no such value has been sourced yet)."
        )
    return alpha


class PoissonYieldBackend:
    name, is_stub = "poisson", False

    def run(self, transport_result, params):
        return run_poisson(transport_result, _require_d0(params), params)


class MurphyYieldBackend:
    name, is_stub = "murphy", False

    def run(self, transport_result, params):
        return run_murphy(transport_result, _require_d0(params), params)


class NegativeBinomialYieldBackend:
    name, is_stub = "negative_binomial", False

    def run(self, transport_result, params):
        return run_negative_binomial(
            transport_result, _require_d0(params), _require_alpha(params), params
        )
