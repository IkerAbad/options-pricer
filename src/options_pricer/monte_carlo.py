"""Monte Carlo pricing under the risk-neutral geometric Brownian motion.

The terminal price is sampled from its exact lognormal distribution, not from an
Euler discretisation, so there is no discretisation bias no matter how large the
expiry is.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .black_scholes import OptionType


@dataclass(frozen=True)
class MonteCarloResult:
    price: float
    standard_error: float
    ci_low: float
    ci_high: float
    paths: int
    antithetic: bool
    mean_terminal: float


def price_european(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    paths: int = 1_000_000,
    seed: int = 42,
    antithetic: bool = True,
) -> MonteCarloResult:
    """Price a European option by simulation, with a 95% confidence interval.

    With antithetic sampling the number of paths is rounded down to an even
    number, because each draw is paired with its mirror image.
    """
    if paths < 2:
        raise ValueError("paths must be at least 2")
    if spot <= 0.0 or strike <= 0.0:
        raise ValueError("spot and strike must be positive")
    if vol <= 0.0:
        raise ValueError("volatility must be positive")
    if expiry <= 0.0:
        raise ValueError("expiry must be positive, in years")

    rng = np.random.default_rng(seed)

    if antithetic:
        half = paths // 2
        draws = rng.standard_normal(half)
        draws = np.concatenate([draws, -draws])
    else:
        draws = rng.standard_normal(paths)

    drift = (rate - 0.5 * vol * vol) * expiry
    diffusion = vol * math.sqrt(expiry) * draws
    terminal = spot * np.exp(drift + diffusion)

    if option_type == "call":
        payoff = np.maximum(terminal - strike, 0.0)
    elif option_type == "put":
        payoff = np.maximum(strike - terminal, 0.0)
    else:
        raise ValueError("option_type must be 'call' or 'put'")

    discounted = math.exp(-rate * expiry) * payoff
    estimate = float(discounted.mean())
    error = float(discounted.std(ddof=1) / math.sqrt(discounted.size))

    return MonteCarloResult(
        price=estimate,
        standard_error=error,
        ci_low=estimate - 1.96 * error,
        ci_high=estimate + 1.96 * error,
        paths=int(discounted.size),
        antithetic=antithetic,
        mean_terminal=float(terminal.mean()),
    )
