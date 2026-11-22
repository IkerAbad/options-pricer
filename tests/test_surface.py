from __future__ import annotations

import math

import pytest

from options_pricer.surface import (
    SviParams,
    calibrate,
    calibrate_surface,
    example_term_structure,
    svi_implied_vol,
    synthetic_market,
    synthetic_surface,
    total_variance,
)

SPOT = 100.0
RATE = 0.03
EXPIRY = 1.0
PARAMS = SviParams(a=0.02, b=0.15, rho=-0.4, m=-0.05, sigma=0.15)
STRIKES = [80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]


def forward() -> float:
    return SPOT * math.exp(RATE * EXPIRY)


def test_total_variance_is_positive_across_the_wing() -> None:
    for k in (-0.5, -0.2, 0.0, 0.2, 0.5):
        assert total_variance(k, PARAMS) > 0.0


def test_implied_volatility_is_in_a_sane_range() -> None:
    for k in (-0.3, -0.1, 0.0, 0.1, 0.3):
        vol = svi_implied_vol(k, EXPIRY, PARAMS)
        assert 0.05 < vol < 0.60


def test_calibration_recovers_a_noiseless_surface() -> None:
    prices = synthetic_market(SPOT, RATE, EXPIRY, STRIKES, PARAMS)
    fitted, rmse = calibrate(SPOT, RATE, EXPIRY, STRIKES, prices)
    assert rmse < 1e-4
    for strike in STRIKES:
        k = math.log(strike / forward())
        assert svi_implied_vol(k, EXPIRY, fitted) == pytest.approx(
            svi_implied_vol(k, EXPIRY, PARAMS), abs=1e-3
        )


def test_calibration_survives_quoted_noise() -> None:
    prices = synthetic_market(SPOT, RATE, EXPIRY, STRIKES, PARAMS, noise=0.001, seed=3)
    _, rmse = calibrate(SPOT, RATE, EXPIRY, STRIKES, prices)
    assert rmse < 0.01


def test_five_quotes_are_required() -> None:
    prices = synthetic_market(SPOT, RATE, EXPIRY, STRIKES[:4], PARAMS)
    with pytest.raises(ValueError):
        calibrate(SPOT, RATE, EXPIRY, STRIKES[:4], prices)


def test_mismatched_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        calibrate(SPOT, RATE, EXPIRY, STRIKES, [1.0] * 5)


def test_surface_calibration_returns_one_fit_per_expiry() -> None:
    structure = example_term_structure()
    expiries = list(structure)
    params = [structure[expiry] for expiry in expiries]
    quotes = synthetic_surface(SPOT, RATE, expiries, STRIKES, params, noise=0.001)

    rows = calibrate_surface(SPOT, RATE, expiries, STRIKES, quotes)

    assert len(rows) == len(expiries)
    assert [row[0] for row in rows] == expiries
    for _, fitted, rmse in rows:
        assert rmse < 0.01
        assert fitted.b > 0.0
        assert -1.0 < fitted.rho < 1.0


def test_example_term_structure_slopes_down() -> None:
    structure = example_term_structure()
    expiries = sorted(structure)
    at_the_money = [svi_implied_vol(0.0, expiry, structure[expiry]) for expiry in expiries]

    for shorter, longer in zip(at_the_money, at_the_money[1:]):
        assert longer < shorter - 1e-6


def test_surface_is_reproducible() -> None:
    structure = example_term_structure()
    expiries = list(structure)
    params = [structure[expiry] for expiry in expiries]

    first = synthetic_surface(SPOT, RATE, expiries, STRIKES, params, noise=0.001, seed=9)
    second = synthetic_surface(SPOT, RATE, expiries, STRIKES, params, noise=0.001, seed=9)

    assert first == second


def test_surface_rejects_mismatched_expiries() -> None:
    with pytest.raises(ValueError):
        calibrate_surface(SPOT, RATE, [0.25, 0.5], STRIKES, [[1.0] * len(STRIKES)])

