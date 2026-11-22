from __future__ import annotations

import pytest

from options_pricer.black_scholes import call_price, put_price
from options_pricer.implied_vol import implied_volatility

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def test_recovers_call_volatility() -> None:
    quoted = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    recovered = implied_volatility(quoted, SPOT, STRIKE, RATE, EXPIRY, "call")
    assert recovered == pytest.approx(VOL, abs=1e-6)


def test_recovers_put_volatility() -> None:
    quoted = put_price(SPOT, 90.0, RATE, 0.35, EXPIRY)
    recovered = implied_volatility(quoted, SPOT, 90.0, RATE, EXPIRY, "put")
    assert recovered == pytest.approx(0.35, abs=1e-6)


def test_recovers_volatility_for_a_skewed_strike() -> None:
    quoted = call_price(SPOT, 130.0, RATE, 0.45, 0.5)
    recovered = implied_volatility(quoted, SPOT, 130.0, RATE, 0.5, "call")
    assert recovered == pytest.approx(0.45, abs=1e-6)


def test_price_below_intrinsic_is_rejected() -> None:
    with pytest.raises(ValueError):
        implied_volatility(1.0, 100.0, 50.0, RATE, EXPIRY, "call")


def test_price_above_the_attainable_range_is_rejected() -> None:
    with pytest.raises(ValueError):
        implied_volatility(500.0, 100.0, 100.0, RATE, EXPIRY, "call")


def test_zero_price_is_rejected() -> None:
    with pytest.raises(ValueError):
        implied_volatility(0.0, SPOT, STRIKE, RATE, EXPIRY, "call")


def test_zero_expiry_is_rejected() -> None:
    with pytest.raises(ValueError):
        implied_volatility(5.0, SPOT, STRIKE, RATE, 0.0, "call")
