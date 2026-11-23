"""SSVI, the surface SVI model of Gatheral and Jacquier.

Total implied variance is

    w(k, theta) = (theta/2) * (1 + rho * phi * k + sqrt((phi * k + rho)^2 + 1 - rho^2))

with k = ln(K/F), theta = w(0) the at-the-money total variance and
phi = eta / theta^gamma. Three parameters describe the whole surface: rho, eta
and gamma. Each expiry contributes its own theta, taken from the at-the-money
quote.

The no-arbitrage condition eta * (1 + |rho|) < 4 is checked after the fit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares


@dataclass(frozen=True)
class SsviParams:
    rho: float
    eta: float
    gamma: float

    def to_dict(self) -> dict[str, float]:
        return {"rho": self.rho, "eta": self.eta, "gamma": self.gamma}

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> SsviParams:
        return cls(rho=float(data["rho"]), eta=float(data["eta"]), gamma=float(data["gamma"]))


def phi_of(theta: float, params: SsviParams) -> float:
    return params.eta / (theta**params.gamma)


def total_variance(k: float, theta: float, params: SsviParams) -> float:
    phi = phi_of(theta, params)
    inner = phi * k + params.rho
    return (
        0.5 * theta * (1.0 + params.rho * phi * k + math.sqrt(inner * inner + 1.0 - params.rho**2))
    )


def implied_vol(k: float, expiry: float, theta: float, params: SsviParams) -> float:
    w = max(total_variance(k, theta, params), 1e-12)
    return math.sqrt(w / expiry)


def is_arbitrage_free(params: SsviParams, tolerance: float = 1e-9) -> bool:
    return params.eta * (1.0 + abs(params.rho)) < 4.0 - tolerance


def atm_total_variance(log_moneyness: list[float], vols: list[float], expiry: float) -> float:
    """Total variance at the money, from the quote closest to k = 0."""
    if not log_moneyness:
        raise ValueError("the slice has no quotes")

    index = min(range(len(log_moneyness)), key=lambda i: abs(log_moneyness[i]))
    return vols[index] * vols[index] * expiry


def calibrate_ssvi(
    expiries: list[float],
    log_moneyness: list[list[float]],
    vols: list[list[float]],
) -> tuple[SsviParams, float, list[float]]:
    """Fit rho, eta and gamma on all slices at once.

    Returns the parameters, the RMSE in implied volatility and the theta of each
    expiry.
    """
    if len(expiries) != len(log_moneyness) or len(expiries) != len(vols):
        raise ValueError("expiries, log_moneyness and vols must have the same length")
    if not expiries:
        raise ValueError("at least one expiry is needed")

    thetas = [
        atm_total_variance(ks, slice_vols, expiry)
        for expiry, ks, slice_vols in zip(expiries, log_moneyness, vols, strict=True)
    ]

    flat: list[tuple[float, float, float, float]] = []
    for expiry, theta, ks, slice_vols in zip(expiries, thetas, log_moneyness, vols, strict=True):
        for k, vol in zip(ks, slice_vols, strict=True):
            flat.append((expiry, theta, k, vol * vol * expiry))

    if len(flat) < 3:
        raise ValueError("at least three quotes are needed for three parameters")

    def residuals(x: np.ndarray) -> np.ndarray:
        candidate = SsviParams(rho=float(x[0]), eta=float(x[1]), gamma=float(x[2]))
        errors = [total_variance(k, theta, candidate) - width for _, theta, k, width in flat]
        violation = max(0.0, candidate.eta * (1.0 + abs(candidate.rho)) - 3.9)
        return np.array([*errors, 100.0 * violation], dtype=float)

    guess = np.array([-0.4, 1.0, 0.4])
    lower = np.array([-0.999, 0.01, 0.01])
    upper = np.array([0.999, 4.0, 0.5])
    guess = np.clip(guess, lower + 1e-6, upper - 1e-6)

    result = least_squares(residuals, guess, bounds=(lower, upper))

    params = SsviParams(rho=float(result.x[0]), eta=float(result.x[1]), gamma=float(result.x[2]))

    squared = [
        (implied_vol(k, expiry, theta, params) - math.sqrt(width / expiry)) ** 2
        for expiry, theta, k, width in flat
    ]
    rmse = math.sqrt(sum(squared) / len(squared))
    return params, rmse, thetas
