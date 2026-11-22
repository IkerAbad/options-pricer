"""Closed-form Black-Scholes prices and Greeks for European options.

Conventions:
- spot, strike and prices are in currency units.
- rate, volatility, dividend yield and expiry are annualised. expiry is in years.
- vega is the derivative with respect to volatility in units (0.20, not 20).
- theta is the derivative with respect to calendar time, per year.
- rho is the derivative with respect to the continuously compounded rate.
- vanna is the cross derivative with respect to spot and volatility.
- volga is the second derivative with respect to volatility.
- charm is minus the derivative of delta with respect to time to expiry, so it
  measures how delta changes as calendar time passes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

OptionType = Literal["call", "put"]

_SQRT_2 = math.sqrt(2.0)
_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    """Standard normal CDF through erfc, which is faster and more accurate in the tails."""
    return 0.5 * math.erfc(-x / _SQRT_2)


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


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


def _d1_d2(
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    dividend_yield: float,
) -> tuple[float, float]:
    sqrt_t = math.sqrt(expiry)
    carry = rate - dividend_yield
    d1 = (math.log(spot / strike) + (carry + 0.5 * vol * vol) * expiry) / (vol * sqrt_t)
    return d1, d1 - vol * sqrt_t


def price(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    dividend_yield: float = 0.0,
) -> float:
    """Black-Scholes price of a European call or put, with a continuous dividend yield."""
    _validate(spot, strike, vol, expiry)
    d1, d2 = _d1_d2(spot, strike, rate, vol, expiry, dividend_yield)
    discount_r = math.exp(-rate * expiry)
    discount_q = math.exp(-dividend_yield * expiry)

    if option_type == "call":
        return spot * discount_q * _norm_cdf(d1) - strike * discount_r * _norm_cdf(d2)
    if option_type == "put":
        return strike * discount_r * _norm_cdf(-d2) - spot * discount_q * _norm_cdf(-d1)
    raise ValueError("option_type must be 'call' or 'put'")


def call_price(
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    dividend_yield: float = 0.0,
) -> float:
    return price("call", spot, strike, rate, vol, expiry, dividend_yield)


def put_price(
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    dividend_yield: float = 0.0,
) -> float:
    return price("put", spot, strike, rate, vol, expiry, dividend_yield)


def greeks(
    option_type: OptionType,
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    expiry: float,
    dividend_yield: float = 0.0,
) -> Greeks:
    """First and second order Greeks, with the conventions listed in the module docstring."""
    _validate(spot, strike, vol, expiry)
    d1, d2 = _d1_d2(spot, strike, rate, vol, expiry, dividend_yield)

    sqrt_t = math.sqrt(expiry)
    discount_r = math.exp(-rate * expiry)
    discount_q = math.exp(-dividend_yield * expiry)
    pdf_d1 = _norm_pdf(d1)
    carry = rate - dividend_yield

    gamma = discount_q * pdf_d1 / (spot * vol * sqrt_t)
    vega = spot * discount_q * pdf_d1 * sqrt_t
    vanna = -discount_q * pdf_d1 * d2 / vol
    volga = vega * d1 * d2 / vol
    charm_common = (
        discount_q
        * pdf_d1
        * (math.log(spot / strike) - (carry + 0.5 * vol * vol) * expiry)
        / (2.0 * vol * expiry * sqrt_t)
    )
    theta_common = -spot * discount_q * pdf_d1 * vol / (2.0 * sqrt_t)

    if option_type == "call":
        delta = discount_q * _norm_cdf(d1)
        theta = (
            theta_common
            + dividend_yield * spot * discount_q * _norm_cdf(d1)
            - rate * strike * discount_r * _norm_cdf(d2)
        )
        rho = strike * expiry * discount_r * _norm_cdf(d2)
        charm = charm_common + dividend_yield * discount_q * _norm_cdf(d1)
    elif option_type == "put":
        delta = -discount_q * _norm_cdf(-d1)
        theta = (
            theta_common
            - dividend_yield * spot * discount_q * _norm_cdf(-d1)
            + rate * strike * discount_r * _norm_cdf(-d2)
        )
        rho = -strike * expiry * discount_r * _norm_cdf(-d2)
        charm = charm_common - dividend_yield * discount_q * _norm_cdf(-d1)
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
