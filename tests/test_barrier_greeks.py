from __future__ import annotations

import pytest

from options_pricer.black_scholes import call_price
from options_pricer.path_dependent import barrier_greeks

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def test_far_barrier_delta_matches_the_european_delta() -> None:
    result = barrier_greeks(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=1_000.0,
        kind="up-and-out",
        paths=200_000,
        seed=5,
    )
    assert result.delta == pytest.approx(0.6368, abs=0.05)
    assert result.price == pytest.approx(call_price(SPOT, STRIKE, RATE, VOL, EXPIRY), abs=0.1)


def test_barrier_vega_is_positive_and_theta_negative() -> None:
    result = barrier_greeks(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=200.0,
        kind="up-and-out",
        paths=200_000,
        seed=5,
    )
    assert result.vega > 0.0
    assert result.theta < 0.0


def test_tight_barrier_has_a_smaller_delta_than_a_loose_one() -> None:
    tight = barrier_greeks(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=110.0,
        kind="up-and-out",
        paths=200_000,
        seed=5,
    )
    loose = barrier_greeks(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=200.0,
        kind="up-and-out",
        paths=200_000,
        seed=5,
    )
    assert tight.delta < loose.delta


def test_same_seed_same_greeks() -> None:
    first = barrier_greeks(
        "put",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=80.0,
        kind="down-and-out",
        paths=50_000,
        seed=9,
    )
    second = barrier_greeks(
        "put",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=80.0,
        kind="down-and-out",
        paths=50_000,
        seed=9,
    )
    assert first == second


def test_invalid_bumps_are_rejected() -> None:
    with pytest.raises(ValueError):
        barrier_greeks(
            "call",
            SPOT,
            STRIKE,
            RATE,
            VOL,
            EXPIRY,
            barrier=120.0,
            bump=0.0,
        )
    with pytest.raises(ValueError):
        barrier_greeks(
            "call",
            SPOT,
            STRIKE,
            RATE,
            VOL,
            0.005,
            barrier=120.0,
            bump=0.01,
        )
