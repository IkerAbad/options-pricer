from __future__ import annotations

import math

import pytest

from options_pricer.black76 import greeks, implied_volatility, price
from options_pricer.black_scholes import call_price, put_price

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0
FORWARD = SPOT * math.exp(RATE * EXPIRY)


def test_black76_reduces_to_black_scholes_without_dividends() -> None:
    assert price("call", FORWARD, STRIKE, RATE, VOL, EXPIRY) == pytest.approx(
        call_price(SPOT, STRIKE, RATE, VOL, EXPIRY), abs=1e-10
    )
    assert price("put", FORWARD, STRIKE, RATE, VOL, EXPIRY) == pytest.approx(
        put_price(SPOT, STRIKE, RATE, VOL, EXPIRY), abs=1e-10
    )


def test_forward_put_call_parity() -> None:
    call = price("call", FORWARD, STRIKE, RATE, VOL, EXPIRY)
    put = price("put", FORWARD, STRIKE, RATE, VOL, EXPIRY)
    assert call - put == pytest.approx(math.exp(-RATE * EXPIRY) * (FORWARD - STRIKE), abs=1e-10)


def test_implied_volatility_round_trip() -> None:
    quoted = price("call", FORWARD, STRIKE, RATE, VOL, EXPIRY)
    recovered = implied_volatility(quoted, FORWARD, STRIKE, RATE, EXPIRY, "call")
    assert recovered == pytest.approx(VOL, abs=1e-8)


def test_forward_greeks() -> None:
    call = greeks("call", FORWARD, STRIKE, RATE, VOL, EXPIRY)
    put = greeks("put", FORWARD, STRIKE, RATE, VOL, EXPIRY)
    discount = math.exp(-RATE * EXPIRY)

    assert call.delta == pytest.approx(discount * 0.6368, abs=1e-3)
    assert put.delta == pytest.approx(discount * -0.3632, abs=1e-3)
    assert call.gamma > 0.0
    assert call.vega > 0.0


def test_price_below_intrinsic_is_rejected() -> None:
    with pytest.raises(ValueError):
        implied_volatility(1.0, 100.0, 50.0, RATE, EXPIRY, "call")


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        price("call", 0.0, STRIKE, RATE, VOL, EXPIRY)
    with pytest.raises(ValueError):
        price("call", FORWARD, STRIKE, RATE, 0.0, EXPIRY)
    with pytest.raises(ValueError):
        price("straddle", FORWARD, STRIKE, RATE, VOL, EXPIRY)
