from __future__ import annotations

import pytest

from options_pricer.path_greeks import (
    asian_greeks_fd,
    asian_greeks_lr,
    barrier_greeks_fd,
    barrier_greeks_lr,
)

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def test_likelihood_ratio_matches_finite_differences_for_an_asian() -> None:
    finite = asian_greeks_fd(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        steps=50,
        paths=200_000,
        seed=7,
    )
    ratio = asian_greeks_lr(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        steps=50,
        paths=1_000_000,
        seed=7,
    )

    assert ratio.delta == pytest.approx(finite.delta, rel=0.03)
    assert ratio.gamma == pytest.approx(finite.gamma, rel=0.15)
    assert ratio.vega == pytest.approx(finite.vega, rel=0.08)


def test_likelihood_ratio_reduces_to_the_european_greeks_with_one_step() -> None:
    ratio = asian_greeks_lr(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        steps=1,
        paths=1_000_000,
        seed=7,
    )
    finite = asian_greeks_fd(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        steps=1,
        paths=1_000_000,
        seed=7,
    )

    assert ratio.delta == pytest.approx(finite.delta, rel=0.01)
    assert ratio.gamma == pytest.approx(finite.gamma, rel=0.10)
    assert ratio.vega == pytest.approx(finite.vega, rel=0.02)


def test_independent_finite_differences_are_noisier() -> None:
    common = barrier_greeks_fd(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        steps=50,
        paths=50_000,
        seed=11,
    )
    independent = barrier_greeks_fd(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        steps=50,
        paths=50_000,
        seed=11,
        independent=True,
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
        seed=11,
    )

    common_error = abs(common.delta - ratio.delta)
    independent_error = abs(independent.delta - ratio.delta)
    assert independent_error >= common_error


def test_barrier_likelihood_ratio_is_finite_near_the_barrier() -> None:
    ratio = barrier_greeks_lr(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=105.0,
        steps=50,
        paths=200_000,
        seed=3,
    )
    for value in (ratio.delta, ratio.gamma, ratio.vega):
        assert value == value  # not NaN
        assert abs(value) < 10.0


def test_invalid_barrier_is_rejected() -> None:
    with pytest.raises(ValueError):
        barrier_greeks_lr("call", SPOT, STRIKE, RATE, VOL, EXPIRY, barrier=-1.0)
    with pytest.raises(ValueError):
        barrier_greeks_fd("call", SPOT, STRIKE, RATE, VOL, EXPIRY, barrier=120.0, kind="sideways")
