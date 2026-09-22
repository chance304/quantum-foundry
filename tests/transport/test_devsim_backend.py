"""Unit tests for devsim_backend.py's caughey_thomas_mobility() -- a pure
function, deliberately no `devsim` import needed (devsim can't even be
imported in this sandbox, see docs/DECISIONS.md), so this runs in the
lightweight CI job.
"""
import pytest

from quantum_foundry.transport.devsim_backend import (
    _CAUGHEY_THOMAS_ELECTRON_PARAMS,
    _CAUGHEY_THOMAS_HOLE_PARAMS,
    caughey_thomas_mobility,
)


def test_mobility_approaches_mu_max_at_low_doping():
    params = _CAUGHEY_THOMAS_ELECTRON_PARAMS
    mobility = caughey_thomas_mobility(doping_cm3=1.0, **params)
    assert mobility == pytest.approx(params["mu_max"], rel=1e-3)


def test_mobility_approaches_mu_min_at_high_doping():
    params = _CAUGHEY_THOMAS_ELECTRON_PARAMS
    mobility = caughey_thomas_mobility(doping_cm3=1e28, **params)
    assert mobility == pytest.approx(params["mu_min"], rel=1e-3)


def test_mobility_decreases_monotonically_with_doping():
    params = _CAUGHEY_THOMAS_HOLE_PARAMS
    dopings = [1e14, 1e16, 1e17, 1e18, 1e20]
    mobilities = [caughey_thomas_mobility(doping_cm3=d, **params) for d in dopings]
    assert mobilities == sorted(mobilities, reverse=True)


def test_mobility_at_n_ref_is_the_arithmetic_midpoint():
    # At doping == n_ref, (N/N_ref)^alpha == 1, so mu = mu_min + (mu_max-mu_min)/2.
    params = _CAUGHEY_THOMAS_ELECTRON_PARAMS
    mobility = caughey_thomas_mobility(doping_cm3=params["n_ref"], **params)
    expected = params["mu_min"] + (params["mu_max"] - params["mu_min"]) / 2
    assert mobility == pytest.approx(expected)
