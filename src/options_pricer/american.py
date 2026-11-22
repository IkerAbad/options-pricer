"""American and European option prices by a Cox-Ross-Rubinstein binomial tree.

The tree is built backwards from the terminal payoffs. At every node the
American value is the maximum of continuation and immediate exercise, while the
European value keeps only the continuation value. Running both on the same tree
gives the early exercise premium without discretisation noise between them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .black_scholes import OptionType


@dataclass(frozen=True)
class BinomialResult:
    american: float
    european: float
    premium: float
    steps: int


def _terminal_prices(spot: float, up: float, down: float, steps: int) -> np.ndarray:
    nodes = np.arange(steps + 1, dtype=float)
    return spot * np.power(up, steps - nodes) * np.power(down, nodes)


def _intrinsic(option_type: OptionType, prices: np.ndarray, strike: float) -> np.ndarray:
    if option_type == "call":
        return np.maximum(prices - strike, 0.0)
    return np.maximum(strike - prices, 0.0)


def _tree(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    steps: int,
    dividend_yield: float,
    american: bool,
) -> float:
    dt = expiry / steps
    up = math.exp(vol * math.sqrt(dt))
    down = 1.0 / up
    growth = math.exp((rate - dividend_yield) * dt)
    probability = (growth - down) / (up - down)
    discount = math.exp(-rate * dt)

    if not 0.0 < probability < 1.0:
        raise ValueError("risk-neutral probability is outside (0, 1): increase the number of steps")

    values = _intrinsic(option_type, _terminal_prices(spot, up, down, steps), strike)

    for step in range(steps - 1, -1, -1):
        values = discount * (probability * values[:-1] + (1.0 - probability) * values[1:])
        if american:
            prices = _terminal_prices(spot, up, down, step)
            values = np.maximum(values, _intrinsic(option_type, prices, strike))

    return float(values[0])


def binomial(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    steps: int = 1_000,
    dividend_yield: float = 0.0,
) -> BinomialResult:
    """Price an American option and its European twin on the same CRR tree."""
    if spot <= 0.0 or strike <= 0.0:
        raise ValueError("spot and strike must be positive")
    if vol <= 0.0:
        raise ValueError("volatility must be positive")
    if expiry <= 0.0:
        raise ValueError("expiry must be positive, in years")
    if steps < 1:
        raise ValueError("steps must be positive")
    if option_type not in ("call", "put"):
        raise ValueError("option_type must be 'call' or 'put'")

    american_value = _tree(
        option_type, spot, strike, rate, vol, expiry, steps, dividend_yield, True
    )
    european_value = _tree(
        option_type, spot, strike, rate, vol, expiry, steps, dividend_yield, False
    )

    return BinomialResult(
        american=american_value,
        european=european_value,
        premium=american_value - european_value,
        steps=steps,
    )
