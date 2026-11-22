from __future__ import annotations

import math

import pytest

from options_pricer.black_scholes import call_price, greeks, price, put_price

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def test_reference_call_price() -> None:
    assert call_price(SPOT, STRIKE, RATE, VOL, EXPIRY) == pytest.approx(10.4506, abs=1e-3)


def test_reference_put_price() -> None:
    assert put_price(SPOT, STRIKE, RATE, VOL, EXPIRY) == pytest.approx(5.5735, abs=1e-3)


def test_put_call_parity() -> None:
    call = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    put = put_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert call - put == pytest.approx(SPOT - STRIKE * math.exp(-RATE * EXPIRY), abs=1e-10)


def test_call_greeks() -> None:
    result = greeks("call", SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.delta == pytest.approx(0.6368, abs=1e-3)
    assert result.gamma > 0.0
    assert result.vega == pytest.approx(37.52, abs=0.01)
    assert result.theta < 0.0
    assert result.rho > 0.0


def test_put_greeks() -> None:
    result = greeks("put", SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.delta == pytest.approx(-0.3632, abs=1e-3)
    assert result.gamma > 0.0
    assert result.theta < 0.0
    assert result.rho < 0.0


def test_deep_in_the_money_call_delta_tends_to_one() -> None:
    result = greeks("call", 500.0, 100.0, RATE, VOL, EXPIRY)
    assert result.delta > 0.99


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        price("call", 0.0, STRIKE, RATE, VOL, EXPIRY)
    with pytest.raises(ValueError):
        price("call", SPOT, 0.0, RATE, VOL, EXPIRY)
    with pytest.raises(ValueError):
        price("call", SPOT, STRIKE, RATE, 0.0, EXPIRY)
    with pytest.raises(ValueError):
        price("call", SPOT, STRIKE, RATE, VOL, 0.0)
    with pytest.raises(ValueError):
        price("digital", SPOT, STRIKE, RATE, VOL, EXPIRY)
