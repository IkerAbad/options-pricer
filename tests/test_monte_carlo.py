from __future__ import annotations

import math

import pytest

from options_pricer.black_scholes import call_price
from options_pricer.monte_carlo import price_european

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def test_monte_carlo_interval_contains_the_analytic_price() -> None:
    result = price_european("call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=200_000, seed=7)
    analytic = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.ci_low <= analytic <= result.ci_high


def test_monte_carlo_put_call_parity_is_exact_per_path() -> None:
    call = price_european("call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=100_000, seed=11)
    put = price_european("put", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=100_000, seed=11)

    assert call.mean_terminal == pytest.approx(put.mean_terminal, abs=1e-9)
    expected = math.exp(-RATE * EXPIRY) * (call.mean_terminal - STRIKE)
    assert call.price - put.price == pytest.approx(expected, abs=1e-9)


def test_same_seed_same_result() -> None:
    first = price_european("call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=10_000, seed=3)
    second = price_european("call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=10_000, seed=3)
    assert first == second


def test_antithetic_sampling_uses_an_even_number_of_paths() -> None:
    result = price_european(
        "call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=1_001, seed=5, antithetic=True
    )
    assert result.paths == 1_000
    assert result.antithetic is True


def test_error_shrinks_with_the_square_root_of_paths() -> None:
    small = price_european("call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=10_000, seed=9)
    large = price_european("call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=1_000_000, seed=9)
    assert large.standard_error < small.standard_error / 5.0


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        price_european("call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=1)
    with pytest.raises(ValueError):
        price_european("call", 0.0, STRIKE, RATE, VOL, EXPIRY)
    with pytest.raises(ValueError):
        price_european("call", SPOT, STRIKE, RATE, 0.0, EXPIRY)
    with pytest.raises(ValueError):
        price_european("call", SPOT, STRIKE, RATE, VOL, 0.0)
    with pytest.raises(ValueError):
        price_european("swaption", SPOT, STRIKE, RATE, VOL, EXPIRY)
