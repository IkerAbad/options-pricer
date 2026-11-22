from __future__ import annotations

import pytest

from options_pricer.american import binomial
from options_pricer.black_scholes import call_price, put_price

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def test_american_call_without_dividends_equals_european() -> None:
    result = binomial("call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=1_000)
    european = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.american == pytest.approx(european, abs=0.01)


def test_american_put_has_an_early_exercise_premium() -> None:
    result = binomial("put", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=1_000)
    assert result.american > result.european
    assert result.premium > 0.05


def test_binomial_european_converges_to_black_scholes() -> None:
    result = binomial("put", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=2_000)
    analytic = put_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.european == pytest.approx(analytic, abs=0.03)


def test_deep_in_the_money_american_put_is_close_to_intrinsic() -> None:
    result = binomial("put", 50.0, 100.0, RATE, VOL, EXPIRY, steps=500)
    assert 49.0 < result.american < 50.5


def test_dividend_yield_makes_an_american_call_worth_exercising_early() -> None:
    without = binomial("call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=800)
    with_dividend = binomial(
        "call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=800, dividend_yield=0.08
    )
    assert without.premium == pytest.approx(0.0, abs=0.01)
    assert with_dividend.premium > 0.0


def test_same_inputs_same_price() -> None:
    first = binomial("put", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=300)
    second = binomial("put", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=300)
    assert first == second


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        binomial("call", 0.0, STRIKE, RATE, VOL, EXPIRY)
    with pytest.raises(ValueError):
        binomial("call", SPOT, STRIKE, RATE, 0.0, EXPIRY)
    with pytest.raises(ValueError):
        binomial("call", SPOT, STRIKE, RATE, VOL, 0.0)
    with pytest.raises(ValueError):
        binomial("call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=0)
    with pytest.raises(ValueError):
        binomial("straddle", SPOT, STRIKE, RATE, VOL, EXPIRY)
