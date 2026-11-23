from __future__ import annotations

import pytest

from options_pricer.black_scholes import call_price
from options_pricer.path_dependent import (
    asian_price,
    barrier_price,
    simulate_paths,
)

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def test_paths_start_at_spot_and_have_the_right_shape() -> None:
    matrix = simulate_paths(SPOT, RATE, VOL, EXPIRY, steps=20, paths=500, seed=1)
    assert matrix.shape == (500, 21)
    assert all(value == SPOT for value in matrix[:, 0])


def test_one_step_asian_matches_the_european_price() -> None:
    result = asian_price("call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=1, paths=200_000, seed=7)
    analytic = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.price == pytest.approx(analytic, abs=0.08)


def test_asian_is_cheaper_than_european_for_a_call() -> None:
    result = asian_price("call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=100, paths=50_000, seed=3)
    analytic = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.price < analytic


def test_barrier_far_away_matches_the_european_price() -> None:
    result = barrier_price(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=1_000.0,
        kind="up-and-out",
        steps=50,
        paths=100_000,
        seed=5,
    )
    analytic = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.price == pytest.approx(analytic, abs=0.08)


def test_up_and_out_barrier_reduces_the_price() -> None:
    european = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    tight = barrier_price(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=110.0,
        kind="up-and-out",
        steps=100,
        paths=50_000,
        seed=5,
    )
    loose = barrier_price(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=180.0,
        kind="up-and-out",
        steps=100,
        paths=50_000,
        seed=5,
    )
    assert tight.price < loose.price < european


def test_in_and_out_add_up_to_the_european_price() -> None:
    out = barrier_price(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        kind="up-and-out",
        steps=100,
        paths=300_000,
        seed=11,
    )
    into = barrier_price(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        kind="up-and-in",
        steps=100,
        paths=300_000,
        seed=11,
    )
    total = out.price + into.price
    european = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert total == pytest.approx(european, abs=0.1)


def test_same_seed_same_price() -> None:
    first = barrier_price(
        "put",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=80.0,
        kind="down-and-out",
        steps=50,
        paths=10_000,
        seed=9,
    )
    second = barrier_price(
        "put",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=80.0,
        kind="down-and-out",
        steps=50,
        paths=10_000,
        seed=9,
    )
    assert first == second


def test_antithetic_reduces_the_standard_error() -> None:
    plain = asian_price("call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=20_000, seed=5)
    anti = asian_price(
        "call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=20_000, seed=5, antithetic=True
    )
    assert anti.standard_error < plain.standard_error


def test_antithetic_path_count_is_even() -> None:
    result = barrier_price(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        paths=10_001,
        antithetic=True,
    )
    assert result.paths == 10_000


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        simulate_paths(0.0, RATE, VOL, EXPIRY)
    with pytest.raises(ValueError):
        simulate_paths(SPOT, RATE, 0.0, EXPIRY)
    with pytest.raises(ValueError):
        simulate_paths(SPOT, RATE, VOL, EXPIRY, steps=0)
    with pytest.raises(ValueError):
        barrier_price("call", SPOT, STRIKE, RATE, VOL, EXPIRY, barrier=120.0, kind="sideways")
    with pytest.raises(ValueError):
        barrier_price("straddle", SPOT, STRIKE, RATE, VOL, EXPIRY, barrier=120.0)
