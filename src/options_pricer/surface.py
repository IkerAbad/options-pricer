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
    initial: SviParams | None = None,
    ridge: float = 1e-3,
) -> tuple[SviParams, float]:
    """Fit an SVI slice to quoted prices. Returns the parameters and the RMSE in volatility.

    When initial is given, the fit starts from those parameters. Chaining slices
    from short to long expiry keeps the term structure stable, which matters
    because SVI parameters are not uniquely identified by a handful of quotes.
    """
    if len(strikes) != len(prices):
        raise ValueError("strikes and prices must have the same length")
    if len(strikes) < 5:
        raise ValueError("SVI has five parameters, at least five quotes are needed")

    forward = spot * math.exp(rate * expiry)
    ks: list[float] = []
    widths: list[float] = []

    for strike, quoted in zip(strikes, prices):
        try:
            vol = implied_volatility(quoted, spot, strike, rate, expiry, option_type)
        except ValueError:
            continue
        ks.append(math.log(strike / forward))
        widths.append(vol * vol * expiry)

    if len(ks) < 5:
        raise ValueError("fewer than five quotes have a valid implied volatility")

    return _fit(expiry, ks, widths, initial, ridge)


def _fit(
    expiry: float,
    ks: list[float],
    widths: list[float],
    initial: SviParams | None,
    ridge: float,
) -> tuple[SviParams, float]:
    def residuals(theta: np.ndarray) -> np.ndarray:
        candidate = SviParams(*[float(value) for value in theta])
        market = np.array(
            [total_variance(k, candidate) - w for k, w in zip(ks, widths)], dtype=float
        )
        shrink = ridge * (theta - guess)
        return np.concatenate([market, shrink])

    if initial is None:
        guess = np.array([max(min(widths) * 0.8, 1e-3), 0.10, -0.30, 0.0, 0.10])
    else:
        guess = np.array(
            [initial.a, initial.b, initial.rho, initial.m, initial.sigma], dtype=float
        )

    lower = np.array([-0.05, 0.0, -0.999, -0.5, 0.01])
    upper = np.array([0.30, 1.0, 0.999, 0.5, 0.50])
    guess = np.clip(guess, lower + 1e-9, upper - 1e-9)

    result = least_squares(residuals, guess, bounds=(lower, upper), loss="soft_l1")
    params = SviParams(*[float(value) for value in result.x])

    squared_errors = [
        (svi_implied_vol(k, expiry, params) - math.sqrt(w / expiry)) ** 2
        for k, w in zip(ks, widths)
    ]
    rmse = math.sqrt(sum(squared_errors) / len(squared_errors))
    return params, rmse


def calibrate_from_vols(
    expiry: float,
    log_moneyness: list[float],
    vols: list[float],
    initial: SviParams | None = None,
    ridge: float = 1e-3,
) -> tuple[SviParams, float]:
    """Fit an SVI slice directly to implied volatilities, without going through prices."""
    if len(log_moneyness) != len(vols):
        raise ValueError("log_moneyness and vols must have the same length")
    if len(vols) < 5:
        raise ValueError("SVI has five parameters, at least five quotes are needed")

    widths = [vol * vol * expiry for vol in vols]
    return _fit(expiry, log_moneyness, widths, initial, ridge)


def calibrate_surface(
    spot: float,
    rate: float,
    expiries: list[float],
    strikes: list[float],
    prices_by_expiry: list[list[float]],
    option_type: OptionType = "call",
) -> list[tuple[float, SviParams, float]]:
    """Calibrate one SVI slice per expiry. Returns (expiry, params, rmse) rows."""
    if len(expiries) != len(prices_by_expiry):
        raise ValueError("expiries and price series must have the same length")
    if not expiries:
        raise ValueError("at least one expiry is needed")

    rows: list[tuple[float, SviParams, float]] = []
    previous: SviParams | None = None

    for expiry, quotes in sorted(zip(expiries, prices_by_expiry)):
        params, rmse = calibrate(
            spot, rate, expiry, strikes, quotes, option_type, initial=previous, ridge=1e-2
        )
        previous = params
        rows.append((expiry, params, rmse))
    return rows


def synthetic_surface(
    spot: float,
    rate: float,
    expiries: list[float],
    strikes: list[float],
    params_by_expiry: list[SviParams],
    option_type: OptionType = "call",
    noise: float = 0.0,
    seed: int = 1,
) -> list[list[float]]:
    """One synthetic quote series per expiry, each with its own noise draw."""
    if len(expiries) != len(params_by_expiry):
        raise ValueError("expiries and parameter sets must have the same length")

    return [
        synthetic_market(
            spot,
            rate,
            expiry,
            strikes,
            params,
            option_type=option_type,
            noise=noise,
            seed=seed + index,
        )
        for index, (expiry, params) in enumerate(zip(expiries, params_by_expiry))
    ]


def example_term_structure() -> dict[float, SviParams]:
    """A downward-sloping term structure used by the CLI and the figures."""
    return {
        0.25: SviParams(a=0.010, b=0.08, rho=-0.45, m=-0.04, sigma=0.12),
        0.50: SviParams(a=0.018, b=0.09, rho=-0.42, m=-0.05, sigma=0.13),
        1.00: SviParams(a=0.032, b=0.10, rho=-0.38, m=-0.06, sigma=0.15),
        2.00: SviParams(a=0.060, b=0.11, rho=-0.32, m=-0.08, sigma=0.18),
    }

