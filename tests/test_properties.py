from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from options_pricer.black_scholes import call_price, greeks, put_price

spot = st.floats(50.0, 150.0)
strike = st.floats(50.0, 150.0)
rate = st.floats(-0.02, 0.10)
vol = st.floats(0.05, 1.0)
expiry = st.floats(0.05, 2.0)


@settings(max_examples=100, deadline=None)
@given(spot, strike, rate, vol, expiry)
def test_put_call_parity_holds_for_any_valid_input(
    spot: float, strike: float, rate: float, vol: float, expiry: float
) -> None:
    call = call_price(spot, strike, rate, vol, expiry)
    put = put_price(spot, strike, rate, vol, expiry)
    expected = spot - strike * math.exp(-rate * expiry)
    assert call - put == pytest.approx(expected, abs=1e-8)


@settings(max_examples=100, deadline=None)
@given(spot, strike, rate, vol, expiry)
def test_call_price_increases_with_spot(
    spot: float, strike: float, rate: float, vol: float, expiry: float
) -> None:
    assert call_price(spot + 1.0, strike, rate, vol, expiry) >= call_price(
        spot, strike, rate, vol, expiry
    )


@settings(max_examples=100, deadline=None)
@given(spot, strike, rate, vol, expiry)
def test_call_price_decreases_with_strike(
    spot: float, strike: float, rate: float, vol: float, expiry: float
) -> None:
    assert call_price(spot, strike, rate, vol, expiry) >= call_price(
        spot, strike + 1.0, rate, vol, expiry
    )


@settings(max_examples=100, deadline=None)
@given(spot, strike, rate, vol, expiry)
def test_greek_bounds(spot: float, strike: float, rate: float, vol: float, expiry: float) -> None:
    result = greeks("call", spot, strike, rate, vol, expiry)
    assert 0.0 <= result.delta <= 1.0
    assert result.gamma >= 0.0
    assert result.vega >= 0.0
    assert -1.0 <= greeks("put", spot, strike, rate, vol, expiry).delta <= 0.0
