"""Path-dependent options priced by Monte Carlo over full price paths.

The paths are simulated under the risk-neutral geometric Brownian motion with
exact log increments, so there is no discretisation bias in the terminal
distribution. Barrier monitoring is discrete: the barrier is checked at the same
steps used to build the path, which is stated in the README.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .black_scholes import OptionType

BarrierKind = str

BARRIER_KINDS = ("up-and-out", "up-and-in", "down-and-out", "down-and-in")


@dataclass(frozen=True)
class PathResult:
    price: float
    standard_error: float
    ci_low: float
    ci_high: float
    paths: int
    steps: int


@dataclass(frozen=True)
class PathGreeks:
    price: float
    delta: float
    vega: float
    theta: float


def simulate_paths(
    spot: float,
    rate: float,
    vol: float,
    expiry: float,
    steps: int = 100,
    paths: int = 50_000,
    seed: int = 42,
    antithetic: bool = False,
) -> np.ndarray:
    """Matrix of shape (paths, steps + 1) with the spot in column zero.

    With antithetic sampling the path count is rounded down to an even number,
    because each draw is paired with its mirror image.
    """
    if spot <= 0.0 or vol <= 0.0 or expiry <= 0.0:
        raise ValueError("spot, volatility and expiry must be positive")
    if steps < 1 or paths < 2:
        raise ValueError("steps must be at least 1 and paths at least 2")

    dt = expiry / steps
    rng = np.random.default_rng(seed)

    if antithetic:
        half = paths // 2
        base = rng.standard_normal((half, steps))
        shocks = np.concatenate([base, -base], axis=0)
    else:
        shocks = rng.standard_normal((paths, steps))

    increments = (rate - 0.5 * vol * vol) * dt + vol * math.sqrt(dt) * shocks
    log_paths = np.cumsum(increments, axis=1)

    return spot * np.exp(np.hstack([np.zeros((shocks.shape[0], 1), dtype=float), log_paths]))


def _summarise(
    payoff: np.ndarray, rate: float, expiry: float, paths: int, steps: int
) -> PathResult:
    discounted = math.exp(-rate * expiry) * payoff
    estimate = float(discounted.mean())
    error = float(discounted.std(ddof=1) / math.sqrt(discounted.size))
    return PathResult(
        price=estimate,
        standard_error=error,
        ci_low=estimate - 1.96 * error,
        ci_high=estimate + 1.96 * error,
        paths=int(discounted.size),
        steps=steps,
    )


def _intrinsic(option_type: OptionType, terminal: np.ndarray, strike: float) -> np.ndarray:
    if option_type == "call":
        return np.maximum(terminal - strike, 0.0)
    if option_type == "put":
        return np.maximum(strike - terminal, 0.0)
    raise ValueError("option_type must be 'call' or 'put'")


def asian_price(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    steps: int = 100,
    paths: int = 50_000,
    seed: int = 42,
    antithetic: bool = False,
) -> PathResult:
    """Arithmetic-average Asian option, averaging the prices after inception."""
    matrix = simulate_paths(spot, rate, vol, expiry, steps, paths, seed, antithetic)
    average = matrix[:, 1:].mean(axis=1)
    payoff = _intrinsic(option_type, average, strike)
    return _summarise(payoff, rate, expiry, paths, steps)


def barrier_price(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    barrier: float,
    kind: BarrierKind = "up-and-out",
    steps: int = 100,
    paths: int = 50_000,
    seed: int = 42,
    antithetic: bool = False,
) -> PathResult:
    """Barrier option with discrete monitoring at the simulation steps."""
    if kind not in BARRIER_KINDS:
        raise ValueError(f"kind must be one of {BARRIER_KINDS}")
    if barrier <= 0.0:
        raise ValueError("barrier must be positive")

    matrix = simulate_paths(spot, rate, vol, expiry, steps, paths, seed, antithetic)
    path_max = matrix.max(axis=1)
    path_min = matrix.min(axis=1)

    if kind == "up-and-out":
        alive = path_max < barrier
    elif kind == "up-and-in":
        alive = path_max >= barrier
    elif kind == "down-and-out":
        alive = path_min > barrier
    else:
        alive = path_min <= barrier

    payoff = np.where(alive, _intrinsic(option_type, matrix[:, -1], strike), 0.0)
    return _summarise(payoff, rate, expiry, paths, steps)


def barrier_greeks(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    barrier: float,
    kind: BarrierKind = "up-and-out",
    steps: int = 100,
    paths: int = 200_000,
    seed: int = 42,
    bump: float = 0.01,
) -> PathGreeks:
    """Delta, vega and theta by bump and reprice with common random numbers.

    Every repricing uses the same seed, so the Monte Carlo noise cancels in the
    finite difference. Gamma is not returned: the second difference is the same
    order as the remaining noise unless the path count is much larger.
    """
    if bump <= 0.0:
        raise ValueError("bump must be positive")
    if expiry <= bump:
        raise ValueError("expiry must be larger than the bump for theta")

    def price_at(new_spot: float, new_vol: float, new_expiry: float) -> float:
        return barrier_price(
            option_type,
            new_spot,
            strike,
            rate,
            new_vol,
            new_expiry,
            barrier,
            kind,
            steps,
            paths,
            seed,
        ).price

    base = price_at(spot, vol, expiry)
    up_spot = price_at(spot * (1.0 + bump), vol, expiry)
    down_spot = price_at(spot * (1.0 - bump), vol, expiry)
    up_vol = price_at(spot, vol + bump, expiry)
    down_vol = price_at(spot, vol - bump, expiry)
    up_time = price_at(spot, vol, expiry + bump)
    down_time = price_at(spot, vol, expiry - bump)

    return PathGreeks(
        price=base,
        delta=(up_spot - down_spot) / (2.0 * spot * bump),
        vega=(up_vol - down_vol) / (2.0 * bump),
        theta=-(up_time - down_time) / (2.0 * bump),
    )
