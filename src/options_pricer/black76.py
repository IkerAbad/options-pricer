"""Black-76 prices for European options on a forward or future.

Black-76 is the same formula as Black-Scholes with the spot replaced by the
forward and the drift removed. It is the standard model for options on futures
and for any market where the forward is quoted directly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.optimize import brentq

from .black_scholes import OptionType, _norm_cdf, _norm_pdf


@dataclass(frozen=True)
class ForwardGreeks:
    delta: float
    gamma: float
    vega: float


def _d1_d2(forward: float, strike: float, vol: float, expiry: float) -> tuple[float, float]:
    if forward <= 0.0 or strike <= 0.0:
        raise ValueError("forward and strike must be positive")
    if vol <= 0.0:
        raise ValueError("volatility must be positive")
    if expiry <= 0.0:
        raise ValueError("expiry must be positive, in years")

    sqrt_t = math.sqrt(expiry)
    d1 = (math.log(forward / strike) + 0.5 * vol * vol * expiry) / (vol * sqrt_t)
    return d1, d1 - vol * sqrt_t


def price(
    option_type: OptionType,
    forward: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
) -> float:
    """Discounted Black-76 price of a European call or put on a forward."""
    d1, d2 = _d1_d2(forward, strike, vol, expiry)
    discount = math.exp(-rate * expiry)

    if option_type == "call":
        return discount * (forward * _norm_cdf(d1) - strike * _norm_cdf(d2))
    if option_type == "put":
        return discount * (strike * _norm_cdf(-d2) - forward * _norm_cdf(-d1))
    raise ValueError("option_type must be 'call' or 'put'")


def greeks(
    option_type: OptionType,
    forward: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
) -> ForwardGreeks:
    """Delta, gamma and vega with respect to the forward."""
    d1, _ = _d1_d2(forward, strike, vol, expiry)
    discount = math.exp(-rate * expiry)
    sqrt_t = math.sqrt(expiry)
    pdf_d1 = _norm_pdf(d1)

    if option_type == "call":
        delta = discount * _norm_cdf(d1)
    elif option_type == "put":
        delta = -discount * _norm_cdf(-d1)
    else:
        raise ValueError("option_type must be 'call' or 'put'")

    return ForwardGreeks(
        delta=delta,
        gamma=discount * pdf_d1 / (forward * vol * sqrt_t),
        vega=discount * forward * pdf_d1 * sqrt_t,
    )


def implied_volatility(
    target_price: float,
    forward: float,
    strike: float,
    rate: float,
    expiry: float,
    option_type: OptionType = "call",
    upper: float = 5.0,
) -> float:
    """Volatility that reproduces target_price under Black-76."""
    if target_price <= 0.0:
        raise ValueError("target price must be positive")

    discount = math.exp(-rate * expiry)
    if option_type == "call":
        intrinsic = discount * max(0.0, forward - strike)
    elif option_type == "put":
        intrinsic = discount * max(0.0, strike - forward)
    else:
        raise ValueError("option_type must be 'call' or 'put'")

    if target_price < intrinsic - 1e-12:
        raise ValueError(f"price {target_price:.6f} is below the intrinsic value {intrinsic:.6f}")

    def gap(vol: float) -> float:
        return price(option_type, forward, strike, rate, vol, expiry) - target_price

    low = 1e-6
    if gap(low) > 0.0:
        raise ValueError("price is above the attainable range")
    if gap(upper) < 0.0:
        raise ValueError(f"price needs a volatility above {upper}")

    return float(brentq(gap, low, upper, xtol=1e-12, rtol=1e-12))
