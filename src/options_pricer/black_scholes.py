"""Closed-form Black-Scholes prices and Greeks for European options.

Conventions:
- spot, strike and prices are in currency units.
- rate, volatility and expiry are annualised. expiry is in years.
- vega is the derivative with respect to volatility in units (0.20, not 20).
- theta is the derivative with respect to calendar time, per year.
- rho is the derivative with respect to the continuously compounded rate.
- vanna is the cross derivative with respect to spot and volatility.
- volga is the second derivative with respect to volatility.
- charm is minus the derivative of delta with respect to time to expiry, so it
  measures how delta changes as calendar time passes. Calls and puts share it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from scipy.stats import norm

OptionType = Literal["call", "put"]


@dataclass(frozen=True)
class Greeks:
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    vanna: float
    volga: float
    charm: float


def _validate(spot: float, strike: float, vol: float, expiry: float) -> None:
    if spot <= 0.0:
        raise ValueError("spot must be positive")
    if strike <= 0.0:
        raise ValueError("strike must be positive")
    if vol <= 0.0:
        raise ValueError("volatility must be positive")
    if expiry <= 0.0:
        raise ValueError("expiry must be positive, in years")


def _d1_d2(spot: float, strike: float, rate: float, vol: float, expiry: float) -> tuple[float, float]:
    sqrt_t = math.sqrt(expiry)
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * expiry) / (vol * sqrt_t)
    return d1, d1 - vol * sqrt_t


def price(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
) -> float:
    """Black-Scholes price of a European call or put."""
    _validate(spot, strike, vol, expiry)
    d1, d2 = _d1_d2(spot, strike, rate, vol, expiry)
    discount = math.exp(-rate * expiry)

    if option_type == "call":
        return spot * norm.cdf(d1) - strike * discount * norm.cdf(d2)
    if option_type == "put":
        return strike * discount * norm.cdf(-d2) - spot * norm.cdf(-d1)
    raise ValueError("option_type must be 'call' or 'put'")


def call_price(spot: float, strike: float, rate: float, vol: float, expiry: float) -> float:
    return price("call", spot, strike, rate, vol, expiry)


def put_price(spot: float, strike: float, rate: float, vol: float, expiry: float) -> float:
    return price("put", spot, strike, rate, vol, expiry)


def greeks(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
) -> Greeks:
    """First-order Greeks, with the conventions listed in the module docstring."""
    _validate(spot, strike, vol, expiry)
    d1, d2 = _d1_d2(spot, strike, rate, vol, expiry)

    sqrt_t = math.sqrt(expiry)
    discount = math.exp(-rate * expiry)
    pdf_d1 = norm.pdf(d1)

    gamma = pdf_d1 / (spot * vol * sqrt_t)
    vega = spot * pdf_d1 * sqrt_t
    vanna = -pdf_d1 * d2 / vol
    volga = vega * d1 * d2 / vol
    charm = (
        pdf_d1
        * (math.log(spot / strike) - (rate + 0.5 * vol * vol) * expiry)
        / (2.0 * vol * expiry * sqrt_t)
    )
    theta_common = -spot * pdf_d1 * vol / (2.0 * sqrt_t)

    if option_type == "call":
        delta = norm.cdf(d1)
        theta = theta_common - rate * strike * discount * norm.cdf(d2)
        rho = strike * expiry * discount * norm.cdf(d2)
    elif option_type == "put":
        delta = norm.cdf(d1) - 1.0
        theta = theta_common + rate * strike * discount * norm.cdf(-d2)
        rho = -strike * expiry * discount * norm.cdf(-d2)
    else:
        raise ValueError("option_type must be 'call' or 'put'")

    return Greeks(
        delta=delta,
        gamma=gamma,
        vega=vega,
        theta=theta,
        rho=rho,
        vanna=vanna,
        volga=volga,
        charm=charm,
    )
