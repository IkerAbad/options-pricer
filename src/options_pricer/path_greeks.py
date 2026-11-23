"""Greeks for path-dependent options by finite differences and likelihood ratio.

Two independent estimators:

- Finite differences with common random numbers (bump and reprice with the same
  seed). Simple and low variance, but the barrier payoff is discontinuous, so a
  bump moves paths across the barrier and the estimator is biased for a finite
  bump.
- Likelihood ratio. The payoff is held fixed and the density is differentiated,
  so the discontinuity of the payoff does not enter the estimator. It is
  unbiased for any bump, at the cost of a higher variance.

Both are compared in `scripts/compare_path_greeks.py`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .black_scholes import OptionType
from .path_dependent import BARRIER_KINDS, BarrierKind, _intrinsic, simulate_paths


@dataclass(frozen=True)
class PathGreeksResult:
    price: float
    delta: float
    gamma: float
    vega: float


def _discount(rate: float, expiry: float) -> float:
    return math.exp(-rate * expiry)


def _scores(
    matrix: np.ndarray,
    spot: float,
    rate: float,
    vol: float,
    expiry: float,
    steps: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Score functions for spot and volatility, plus the spot gamma term.

    The spot only enters the first transition, because the log-returns are
    independent of the initial level. The volatility enters every transition, so
    its score is a sum over steps.
    """
    dt = expiry / steps
    log_returns = np.diff(np.log(matrix), axis=1)
    drift = (rate - 0.5 * vol * vol) * dt
    residuals = log_returns - drift

    first = residuals[:, 0]
    score_spot = first / (spot * vol * vol * dt)
    score_gamma = -(1.0 + first) / (spot * spot * vol * vol * dt)
    score_vol = np.sum(-(1.0 + residuals) / vol + residuals * residuals / (vol**3 * dt), axis=1)
    return score_spot, score_gamma, score_vol


def _asian_payoff(matrix: np.ndarray, option_type: OptionType, strike: float) -> np.ndarray:
    average = matrix[:, 1:].mean(axis=1)
    return _intrinsic(option_type, average, strike)


def _barrier_payoff(
    matrix: np.ndarray,
    option_type: OptionType,
    strike: float,
    barrier: float,
    kind: BarrierKind,
) -> np.ndarray:
    terminal = _intrinsic(option_type, matrix[:, -1], strike)
    if kind.startswith("up"):
        crossed = matrix.max(axis=1) >= barrier
    else:
        crossed = matrix.min(axis=1) <= barrier

    if kind.endswith("out"):
        return np.where(crossed, 0.0, terminal)
    return np.where(crossed, terminal, 0.0)


def asian_greeks_lr(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    steps: int = 100,
    paths: int = 100_000,
    seed: int = 42,
) -> PathGreeksResult:
    matrix = simulate_paths(spot, rate, vol, expiry, steps, paths, seed)
    payoff = _asian_payoff(matrix, option_type, strike)
    score_spot, score_gamma, score_vol = _scores(matrix, spot, rate, vol, expiry, steps)
    discount = _discount(rate, expiry)

    return PathGreeksResult(
        price=discount * float(payoff.mean()),
        delta=discount * float((payoff * score_spot).mean()),
        gamma=discount * float((payoff * (score_spot * score_spot + score_gamma)).mean()),
        vega=discount * float((payoff * score_vol).mean()),
    )


def barrier_greeks_lr(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    barrier: float,
    kind: BarrierKind = "up-and-out",
    steps: int = 100,
    paths: int = 100_000,
    seed: int = 42,
) -> PathGreeksResult:
    if kind not in BARRIER_KINDS:
        raise ValueError(f"kind must be one of {BARRIER_KINDS}")
    if barrier <= 0.0:
        raise ValueError("barrier must be positive")

    matrix = simulate_paths(spot, rate, vol, expiry, steps, paths, seed)
    payoff = _barrier_payoff(matrix, option_type, strike, barrier, kind)
    score_spot, score_gamma, score_vol = _scores(matrix, spot, rate, vol, expiry, steps)
    discount = _discount(rate, expiry)

    return PathGreeksResult(
        price=discount * float(payoff.mean()),
        delta=discount * float((payoff * score_spot).mean()),
        gamma=discount * float((payoff * (score_spot * score_spot + score_gamma)).mean()),
        vega=discount * float((payoff * score_vol).mean()),
    )


def _bump(spot: float, vol: float, relative: float) -> tuple[float, float, float, float]:
    spot_up = spot * (1.0 + relative)
    spot_down = spot * (1.0 - relative)
    vol_up = vol + relative
    vol_down = vol - relative
    return spot_up, spot_down, vol_up, vol_down


def asian_greeks_fd(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    steps: int = 100,
    paths: int = 100_000,
    seed: int = 42,
    bump: float = 0.01,
    independent: bool = False,
) -> PathGreeksResult:
    """Finite differences with common random numbers unless independent is True."""
    from .path_dependent import asian_price

    spot_up, spot_down, vol_up, vol_down = _bump(spot, vol, bump)

    def price_at(new_spot: float, new_vol: float, new_seed: int) -> float:
        return asian_price(
            option_type,
            new_spot,
            strike,
            rate,
            new_vol,
            expiry,
            steps=steps,
            paths=paths,
            seed=new_seed,
        ).price

    seed_up_spot = seed + 1 if independent else seed
    seed_down_spot = seed + 2 if independent else seed
    seed_up_vol = seed + 3 if independent else seed
    seed_down_vol = seed + 4 if independent else seed

    base = price_at(spot, vol, seed)
    up_spot = price_at(spot_up, vol, seed_up_spot)
    down_spot = price_at(spot_down, vol, seed_down_spot)
    up_vol = price_at(spot, vol_up, seed_up_vol)
    down_vol = price_at(spot, vol_down, seed_down_vol)

    return PathGreeksResult(
        price=base,
        delta=(up_spot - down_spot) / (2.0 * spot * bump),
        gamma=(up_spot - 2.0 * base + down_spot) / ((spot * bump) ** 2),
        vega=(up_vol - down_vol) / (2.0 * bump),
    )


def barrier_greeks_fd(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    barrier: float,
    kind: BarrierKind = "up-and-out",
    steps: int = 100,
    paths: int = 100_000,
    seed: int = 42,
    bump: float = 0.01,
    independent: bool = False,
) -> PathGreeksResult:
    """Finite differences with common random numbers unless independent is True."""
    from .path_dependent import barrier_price

    if kind not in BARRIER_KINDS:
        raise ValueError(f"kind must be one of {BARRIER_KINDS}")
    if barrier <= 0.0:
        raise ValueError("barrier must be positive")

    spot_up, spot_down, vol_up, vol_down = _bump(spot, vol, bump)

    def price_at(new_spot: float, new_vol: float, new_seed: int) -> float:
        return barrier_price(
            option_type,
            new_spot,
            strike,
            rate,
            new_vol,
            expiry,
            barrier=barrier,
            kind=kind,
            steps=steps,
            paths=paths,
            seed=new_seed,
        ).price

    seed_up_spot = seed + 1 if independent else seed
    seed_down_spot = seed + 2 if independent else seed
    seed_up_vol = seed + 3 if independent else seed
    seed_down_vol = seed + 4 if independent else seed

    base = price_at(spot, vol, seed)
    up_spot = price_at(spot_up, vol, seed_up_spot)
    down_spot = price_at(spot_down, vol, seed_down_spot)
    up_vol = price_at(spot, vol_up, seed_up_vol)
    down_vol = price_at(spot, vol_down, seed_down_vol)

    return PathGreeksResult(
        price=base,
        delta=(up_spot - down_spot) / (2.0 * spot * bump),
        gamma=(up_spot - 2.0 * base + down_spot) / ((spot * bump) ** 2),
        vega=(up_vol - down_vol) / (2.0 * bump),
    )
