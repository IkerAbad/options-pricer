"""Regression test against a frozen set of numerical results.

If a value changes on purpose, rerun `python scripts/write_reference.py` and
review the diff. If it changes by accident, this test fails.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from options_pricer import black76
from options_pricer.american import binomial
from options_pricer.black_scholes import call_price, greeks, put_price
from options_pricer.implied_vol import implied_volatility
from options_pricer.path_dependent import asian_price, barrier_price
from options_pricer.path_greeks import (
    asian_greeks_fd,
    asian_greeks_lr,
    barrier_greeks_fd,
    barrier_greeks_lr,
)
from options_pricer.surface import SviParams, calibrate, calibrate_from_vols, synthetic_market

REFERENCE = Path(__file__).parent / "data" / "reference_values.json"
VALUES = json.loads(REFERENCE.read_text(encoding="utf-8"))

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def test_black_scholes_prices() -> None:
    assert call_price(SPOT, STRIKE, RATE, VOL, EXPIRY) == pytest.approx(
        VALUES["black_scholes_call"], abs=1e-12
    )
    assert put_price(SPOT, STRIKE, RATE, VOL, EXPIRY) == pytest.approx(
        VALUES["black_scholes_put"], abs=1e-12
    )


def test_greeks() -> None:
    result = greeks("call", SPOT, STRIKE, RATE, VOL, EXPIRY)
    for name in ("delta", "gamma", "vega", "theta", "rho", "vanna", "volga", "charm"):
        assert getattr(result, name) == pytest.approx(VALUES[name], abs=1e-12)


def test_black76_and_implied_volatility() -> None:
    forward = SPOT * math.exp(RATE)
    assert black76.price("call", forward, STRIKE, RATE, VOL, EXPIRY) == pytest.approx(
        VALUES["black76_call"], abs=1e-10
    )
    assert implied_volatility(
        VALUES["black_scholes_call"], SPOT, STRIKE, RATE, EXPIRY, "call"
    ) == pytest.approx(VALUES["implied_vol"], abs=1e-12)


def test_american_put() -> None:
    assert binomial("put", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=1_000).american == pytest.approx(
        VALUES["american_put"], abs=1e-10
    )


def test_path_dependent_prices() -> None:
    assert asian_price(
        "call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=50, paths=20_000, seed=7
    ).price == pytest.approx(VALUES["asian_call"], abs=1e-9)

    assert barrier_price(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        steps=50,
        paths=20_000,
        seed=7,
    ).price == pytest.approx(VALUES["barrier_discrete"], abs=1e-9)

    assert barrier_price(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        steps=50,
        paths=20_000,
        seed=7,
        continuous=True,
    ).price == pytest.approx(VALUES["barrier_continuous"], abs=1e-9)


def test_svi_calibration_rmse() -> None:
    truth = SviParams(a=0.02, b=0.15, rho=-0.4, m=-0.05, sigma=0.15)
    strikes = [80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]
    quotes = synthetic_market(SPOT, 0.03, EXPIRY, strikes, truth, noise=0.001, seed=1)
    _, rmse = calibrate(SPOT, 0.03, EXPIRY, strikes, quotes)
    assert rmse == pytest.approx(VALUES["svi_rmse"], abs=1e-9)


def test_asian_greeks() -> None:
    finite = asian_greeks_fd(
        "call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=50, paths=200_000, seed=7
    )
    ratio = asian_greeks_lr(
        "call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=50, paths=1_000_000, seed=7
    )

    assert finite.delta == pytest.approx(VALUES["asian_fd_delta"], rel=1e-9)
    assert finite.gamma == pytest.approx(VALUES["asian_fd_gamma"], rel=1e-9)
    assert finite.vega == pytest.approx(VALUES["asian_fd_vega"], rel=1e-9)
    assert ratio.delta == pytest.approx(VALUES["asian_lr_delta"], rel=1e-9)
    assert ratio.gamma == pytest.approx(VALUES["asian_lr_gamma"], rel=1e-9)
    assert ratio.vega == pytest.approx(VALUES["asian_lr_vega"], rel=1e-9)


def test_barrier_greeks() -> None:
    finite = barrier_greeks_fd(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        steps=50,
        paths=200_000,
        seed=7,
    )
    ratio = barrier_greeks_lr(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        steps=50,
        paths=1_000_000,
        seed=7,
    )

    assert finite.delta == pytest.approx(VALUES["barrier_fd_delta"], rel=1e-9)
    assert finite.gamma == pytest.approx(VALUES["barrier_fd_gamma"], rel=1e-9)
    assert finite.vega == pytest.approx(VALUES["barrier_fd_vega"], rel=1e-9)
    assert ratio.delta == pytest.approx(VALUES["barrier_lr_delta"], rel=1e-9)
    assert ratio.gamma == pytest.approx(VALUES["barrier_lr_gamma"], rel=1e-9)
    assert ratio.vega == pytest.approx(VALUES["barrier_lr_vega"], rel=1e-9)


def test_history_snapshot_calibration() -> None:
    from options_pricer.real_data import build_slice, load_history_day

    path = Path(__file__).parent.parent / "data" / "history" / "binance_btc_options_2026-11-22.csv"
    _, quotes = load_history_day(path)
    group = [quote for quote in quotes if quote.expiry == "2026-12-25"]
    current = build_slice(group)

    params, rmse = calibrate_from_vols(
        current.years,
        current.log_moneyness,
        current.vols,
        ridge=1e-2,
        weights=current.weights,
    )

    assert current.forward == pytest.approx(61_405.0, abs=0.01)
    assert params.a == pytest.approx(0.013027329996104087, rel=1e-5)
    assert params.b == pytest.approx(0.10042507504525912, rel=1e-5)
    assert params.rho == pytest.approx(-0.36876238286479557, rel=1e-5)
    assert params.m == pytest.approx(-0.028297808792024263, rel=1e-5)
    assert params.sigma == pytest.approx(0.10515185243938024, rel=1e-5)
    assert rmse == pytest.approx(0.12243067430732418, rel=1e-5)
