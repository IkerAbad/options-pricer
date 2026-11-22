"""SVI total-variance parametrisation and calibration from option prices.

The raw SVI form used here is

    w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2))

where k = ln(K / F) is the log-moneyness and w = sigma_implied^2 * T is the
total implied variance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from . import black_scholes
from .black_scholes import OptionType
from .implied_vol import implied_volatility


@dataclass(frozen=True)
class SviParams:
    a: float
    b: float
    rho: float
    m: float
    sigma: float


def total_variance(k: float, params: SviParams) -> float:
    d = k - params.m
    return params.a + params.b * (params.rho * d + math.sqrt(d * d + params.sigma * params.sigma))


def svi_implied_vol(k: float, expiry: float, params: SviParams) -> float:
    w = max(total_variance(k, params), 1e-12)
    return math.sqrt(w / expiry)


def synthetic_market(
    spot: float,
    rate: float,
    expiry: float,
    strikes: list[float],
    params: SviParams,
    option_type: OptionType = "call",
    noise: float = 0.0,
    seed: int = 1,
) -> list[float]:
    """Option prices generated from an SVI surface, with optional relative noise."""
    rng = np.random.default_rng(seed)
    forward = spot * math.exp(rate * expiry)
    prices: list[float] = []

    for strike in strikes:
        k = math.log(strike / forward)
        vol = svi_implied_vol(k, expiry, params)
        value = black_scholes.price(option_type, spot, strike, rate, vol, expiry)
        if noise > 0.0:
            value *= 1.0 + float(rng.normal(0.0, noise))
        prices.append(value)

    return prices


def calibrate(
    spot: float,
    rate: float,
    expiry: float,
    strikes: list[float],
    prices: list[float],
    option_type: OptionType = "call",
) -> tuple[SviParams, float]:
    """Fit an SVI slice to quoted prices. Returns the parameters and the RMSE in volatility."""
    if len(strikes) != len(prices):
        raise ValueError("strikes and prices must have the same length")
    if len(strikes) < 5:
        raise ValueError("SVI has five parameters, at least five quotes are needed")

    forward = spot * math.exp(rate * expiry)
    ks: list[float] = []
    widths: list[float] = []
    vols: list[float] = []

    for strike, quoted in zip(strikes, prices):
        try:
            vol = implied_volatility(quoted, spot, strike, rate, expiry, option_type)
        except ValueError:
            continue
        ks.append(math.log(strike / forward))
        widths.append(vol * vol * expiry)
        vols.append(vol)

    if len(ks) < 5:
        raise ValueError("fewer than five quotes have a valid implied volatility")

    def residuals(theta: np.ndarray) -> np.ndarray:
        candidate = SviParams(*[float(value) for value in theta])
        return np.array(
            [total_variance(k, candidate) - w for k, w in zip(ks, widths)], dtype=float
        )

    initial = np.array(
        [max(min(widths), 1e-4), 0.1, -0.3, 0.0, 0.1], dtype=float
    )
    lower = np.array([-1.0, 0.0, -0.999, -2.0, 0.01])
    upper = np.array([1.0, 5.0, 0.999, 2.0, 2.0])
    initial = np.clip(initial, lower + 1e-9, upper - 1e-9)

    result = least_squares(residuals, initial, bounds=(lower, upper), loss="soft_l1")
    params = SviParams(*[float(value) for value in result.x])

    squared_errors = [
        (svi_implied_vol(k, expiry, params) - vol) ** 2 for k, vol in zip(ks, vols)
    ]
    rmse = math.sqrt(sum(squared_errors) / len(squared_errors))
    return params, rmse
