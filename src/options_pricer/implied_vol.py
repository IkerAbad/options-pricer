"""Implied volatility by root finding on the Black-Scholes price."""

from __future__ import annotations

import math

from scipy.optimize import brentq

from . import black_scholes
from .black_scholes import OptionType


def intrinsic_value(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    expiry: float,
) -> float:
    discount = math.exp(-rate * expiry)
    if option_type == "call":
        return max(0.0, spot - strike * discount)
    if option_type == "put":
        return max(0.0, strike * discount - spot)
    raise ValueError("option_type must be 'call' or 'put'")


def implied_volatility(
    target_price: float,
    spot: float,
    strike: float,
    rate: float,
    expiry: float,
    option_type: OptionType = "call",
    upper: float = 5.0,
) -> float:
    """Volatility that reproduces target_price under Black-Scholes.

    Raises ValueError when the price is outside the no-arbitrage range, which
    means no positive volatility can produce it.
    """
    if target_price <= 0.0:
        raise ValueError("target price must be positive")
    if expiry <= 0.0:
        raise ValueError("expiry must be positive, in years")

    floor = intrinsic_value(option_type, spot, strike, rate, expiry)
    if target_price < floor - 1e-12:
        raise ValueError(
            f"price {target_price:.6f} is below the intrinsic value {floor:.6f}"
        )

    def gap(vol: float) -> float:
        return black_scholes.price(option_type, spot, strike, rate, vol, expiry) - target_price

    low = 1e-6
    high = upper

    if gap(low) > 0.0:
        raise ValueError("price is above the attainable range")
    if gap(high) < 0.0:
        raise ValueError(f"price needs a volatility above {upper}")

    return float(brentq(gap, low, high, xtol=1e-12, rtol=1e-12))
