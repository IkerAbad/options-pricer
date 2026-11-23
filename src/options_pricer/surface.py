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
from scipy.optimize import least_squares, minimize

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

    def to_dict(self) -> dict[str, float]:
        """Plain dictionary, ready to serialise as JSON."""
        return {
            "a": self.a,
            "b": self.b,
            "rho": self.rho,
            "m": self.m,
            "sigma": self.sigma,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> SviParams:
        return cls(
            a=float(data["a"]),
            b=float(data["b"]),
            rho=float(data["rho"]),
            m=float(data["m"]),
            sigma=float(data["sigma"]),
        )


def total_variance(k: float, params: SviParams) -> float:
    d = k - params.m
    return params.a + params.b * (params.rho * d + math.sqrt(d * d + params.sigma * params.sigma))


def total_variance_derivatives(k: float, params: SviParams) -> tuple[float, float, float]:
    """Total variance and its first two derivatives with respect to log-moneyness."""
    d = k - params.m
    root = math.sqrt(d * d + params.sigma * params.sigma)
    w = params.a + params.b * (params.rho * d + root)
    w1 = params.b * (params.rho + d / root)
    w2 = params.b * params.sigma * params.sigma / (root * root * root)
    return w, w1, w2


def butterfly_g(k: float, params: SviParams) -> float:
    """Gatheral's butterfly function. The slice is free of butterfly arbitrage where g >= 0."""
    w, w1, w2 = total_variance_derivatives(k, params)
    if w <= 0.0:
        return -math.inf

    first = (1.0 - k * w1 / (2.0 * w)) ** 2
    second = (w1 * w1 / 4.0) * (1.0 / w + 0.25)
    return first - second + 0.5 * w2


def butterfly_profile(
    params: SviParams, k_min: float, k_max: float, points: int = 201
) -> list[tuple[float, float]]:
    step = (k_max - k_min) / (points - 1)
    return [(k_min + i * step, butterfly_g(k_min + i * step, params)) for i in range(points)]


def butterfly_share_below_zero(
    params: SviParams, k_min: float, k_max: float, points: int = 201, tol: float = 1e-8
) -> float:
    profile = butterfly_profile(params, k_min, k_max, points)
    below = sum(1 for _, value in profile if value < -tol)
    return below / len(profile)


def calendar_gap(
    short: SviParams,
    long: SviParams,
    k_min: float,
    k_max: float,
    points: int = 201,
) -> float:
    """Smallest increase in total variance between two slices.

    Calendar arbitrage exists when total variance decreases with maturity, so a
    non-negative gap is the condition to check.
    """
    step = (k_max - k_min) / (points - 1)
    smallest = math.inf
    for i in range(points):
        k = k_min + i * step
        smallest = min(smallest, total_variance(k, long) - total_variance(k, short))
    return smallest


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
    floor: SviParams | None = None,
    floor_weight: float = 10.0,
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

    for strike, quoted in zip(strikes, prices, strict=True):
        try:
            vol = implied_volatility(quoted, spot, strike, rate, expiry, option_type)
        except ValueError:
            continue
        ks.append(math.log(strike / forward))
        widths.append(vol * vol * expiry)

    if len(ks) < 5:
        raise ValueError("fewer than five quotes have a valid implied volatility")

    return _fit(expiry, ks, widths, initial, ridge, floor, floor_weight)


def _fit(
    expiry: float,
    ks: list[float],
    widths: list[float],
    initial: SviParams | None,
    ridge: float,
    floor: SviParams | None = None,
    floor_weight: float = 10.0,
) -> tuple[SviParams, float]:
    calendar_grid = np.linspace(-1.0, 1.0, 41)
    floor_values = (
        np.array([total_variance(k, floor) for k in calendar_grid]) if floor is not None else None
    )

    def residuals(theta: np.ndarray) -> np.ndarray:
        candidate = SviParams(*[float(value) for value in theta])
        market = np.array(
            [total_variance(k, candidate) - w for k, w in zip(ks, widths, strict=True)], dtype=float
        )
        shrink = ridge * (theta - guess)
        parts = [market, shrink]

        if floor_values is not None:
            candidate_values = np.array([total_variance(k, candidate) for k in calendar_grid])
            parts.append(floor_weight * np.maximum(0.0, floor_values - candidate_values))

        return np.concatenate(parts)

    if initial is None:
        guess = np.array([max(min(widths) * 0.8, 1e-3), 0.10, -0.30, 0.0, 0.10])
    else:
        guess = np.array([initial.a, initial.b, initial.rho, initial.m, initial.sigma], dtype=float)

    lower = np.array([-0.05, 0.0, -0.999, -0.5, 0.01])
    upper = np.array([0.30, 1.0, 0.999, 0.5, 0.50])
    guess = np.clip(guess, lower + 1e-9, upper - 1e-9)

    result = least_squares(residuals, guess, bounds=(lower, upper), loss="soft_l1")
    params = SviParams(*[float(value) for value in result.x])

    squared_errors = [
        (svi_implied_vol(k, expiry, params) - math.sqrt(w / expiry)) ** 2
        for k, w in zip(ks, widths, strict=True)
    ]
    rmse = math.sqrt(sum(squared_errors) / len(squared_errors))
    return params, rmse


def _fit_hard(
    expiry: float,
    ks: list[float],
    widths: list[float],
    initial: SviParams | None,
    ridge: float,
    floor: SviParams,
) -> tuple[SviParams, float]:
    """Fit with the calendar constraint imposed as an explicit inequality.

    least_squares only takes box bounds, so this path uses SLSQP with one
    inequality per grid point. It is slower and can fail to converge, which is
    why it is opt-in.
    """
    grid = np.linspace(-1.0, 1.0, 41)
    floor_values = np.array([total_variance(k, floor) for k in grid])

    if initial is None:
        guess = np.array([max(min(widths) * 0.8, 1e-3), 0.10, -0.30, 0.0, 0.10])
    else:
        guess = np.array([initial.a, initial.b, initial.rho, initial.m, initial.sigma], dtype=float)

    lower = np.array([-0.05, 0.0, -0.999, -0.5, 0.01])
    upper = np.array([0.30, 1.0, 0.999, 0.5, 0.50])
    guess = np.clip(guess, lower + 1e-9, upper - 1e-9)

    def objective(theta: np.ndarray) -> float:
        candidate = SviParams(*[float(value) for value in theta])
        market = sum(
            (total_variance(k, candidate) - w) ** 2 for k, w in zip(ks, widths, strict=True)
        )
        shrink = ridge * float(np.sum((theta - guess) ** 2))
        return market + shrink

    def constraint(theta: np.ndarray) -> np.ndarray:
        candidate = SviParams(*[float(value) for value in theta])
        return np.array(
            [
                total_variance(k, candidate) - value
                for k, value in zip(grid, floor_values, strict=True)
            ]
        )

    result = minimize(
        objective,
        guess,
        method="SLSQP",
        bounds=list(zip(lower, upper, strict=True)),
        constraints=[{"type": "ineq", "fun": constraint}],
        options={"maxiter": 1_000, "ftol": 1e-12},
    )

    params = SviParams(*[float(value) for value in result.x])
    squared_errors = [
        (svi_implied_vol(k, expiry, params) - math.sqrt(w / expiry)) ** 2
        for k, w in zip(ks, widths, strict=True)
    ]
    rmse = math.sqrt(sum(squared_errors) / len(squared_errors))
    return params, rmse


def calibrate_from_vols(
    expiry: float,
    log_moneyness: list[float],
    vols: list[float],
    initial: SviParams | None = None,
    ridge: float = 1e-3,
    floor: SviParams | None = None,
    floor_weight: float = 10.0,
    hard_calendar: bool = False,
) -> tuple[SviParams, float]:
    """Fit an SVI slice directly to implied volatilities, without going through prices.

    When floor is given, total variance is pushed to stay above that slice at
    every point of the grid, which removes calendar arbitrage against the
    previous maturity. With hard_calendar the constraint is imposed by SLSQP
    instead of a penalty.
    """
    if len(log_moneyness) != len(vols):
        raise ValueError("log_moneyness and vols must have the same length")
    if len(vols) < 5:
        raise ValueError("SVI has five parameters, at least five quotes are needed")

    widths = [vol * vol * expiry for vol in vols]

    if hard_calendar and floor is not None:
        return _fit_hard(expiry, log_moneyness, widths, initial, ridge, floor)

    return _fit(expiry, log_moneyness, widths, initial, ridge, floor, floor_weight)


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

    for expiry, quotes in sorted(zip(expiries, prices_by_expiry, strict=True)):
        params, rmse = calibrate(
            spot,
            rate,
            expiry,
            strikes,
            quotes,
            option_type,
            initial=previous,
            ridge=1e-2,
            floor=previous,
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
        for index, (expiry, params) in enumerate(zip(expiries, params_by_expiry, strict=True))
    ]


def example_term_structure() -> dict[float, SviParams]:
    """A downward-sloping term structure used by the CLI and the figures."""
    return {
        0.25: SviParams(a=0.010, b=0.08, rho=-0.45, m=-0.04, sigma=0.12),
        0.50: SviParams(a=0.018, b=0.09, rho=-0.42, m=-0.05, sigma=0.13),
        1.00: SviParams(a=0.032, b=0.10, rho=-0.38, m=-0.06, sigma=0.15),
        2.00: SviParams(a=0.060, b=0.11, rho=-0.32, m=-0.08, sigma=0.18),
    }


@dataclass(frozen=True)
class BootstrapResult:
    samples: int
    lower: dict[str, float]
    upper: dict[str, float]
    rmse_low: float
    rmse_high: float


def bootstrap_slice(
    spot: float,
    rate: float,
    expiry: float,
    strikes: list[float],
    prices: list[float],
    option_type: OptionType = "call",
    samples: int = 200,
    seed: int = 1,
    confidence: float = 0.95,
) -> BootstrapResult:
    """Resample the calibration residuals to put an interval around each SVI parameter.

    The residuals come from the fitted model, not from the data, so this measures
    how stable the fit is under the noise the model could not explain. It is not
    a confidence interval for the true market parameters.
    """
    if samples < 10:
        raise ValueError("at least ten samples are needed")

    forward = spot * math.exp(rate * expiry)
    fitted, _ = calibrate(spot, rate, expiry, strikes, prices, option_type)

    model_prices: list[float] = []
    for strike in strikes:
        k = math.log(strike / forward)
        vol = svi_implied_vol(k, expiry, fitted)
        model_prices.append(black_scholes.price(option_type, spot, strike, rate, vol, expiry))

    residuals = [quoted - model for quoted, model in zip(prices, model_prices, strict=True)]
    rng = np.random.default_rng(seed)

    collected: list[SviParams] = []
    rmses: list[float] = []

    for _ in range(samples):
        perturbed = [max(1e-6, model + float(rng.choice(residuals))) for model in model_prices]
        try:
            params, rmse = calibrate(
                spot, rate, expiry, strikes, perturbed, option_type, initial=fitted
            )
        except ValueError:
            continue
        collected.append(params)
        rmses.append(rmse)

    if len(collected) < 10:
        raise ValueError("too few bootstrap samples converged")

    tail = 100.0 * (1.0 - confidence) / 2.0
    lower: dict[str, float] = {}
    upper: dict[str, float] = {}

    for name in ("a", "b", "rho", "m", "sigma"):
        values = np.array([getattr(params, name) for params in collected])
        lower[name] = float(np.percentile(values, tail))
        upper[name] = float(np.percentile(values, 100.0 - tail))

    return BootstrapResult(
        samples=len(collected),
        lower=lower,
        upper=upper,
        rmse_low=float(np.percentile(rmses, tail)),
        rmse_high=float(np.percentile(rmses, 100.0 - tail)),
    )


def out_of_sample_rmse(
    spot: float,
    rate: float,
    expiry: float,
    strikes: list[float],
    prices: list[float],
    option_type: OptionType = "call",
) -> tuple[float, float]:
    """Fit on two thirds of the strikes and measure the error on the rest.

    Returns (train_rmse, test_rmse) in implied volatility. The split is
    deterministic: every third strike, ordered by strike, goes to the test set.
    """
    ordered = sorted(zip(strikes, prices, strict=True))
    train = [(strike, quoted) for index, (strike, quoted) in enumerate(ordered) if index % 3 != 2]
    test = [(strike, quoted) for index, (strike, quoted) in enumerate(ordered) if index % 3 == 2]

    if len(train) < 5 or not test:
        raise ValueError("not enough strikes to split into train and test")

    train_strikes = [strike for strike, _ in train]
    train_prices = [quoted for _, quoted in train]

    params, train_rmse = calibrate(spot, rate, expiry, train_strikes, train_prices, option_type)

    forward = spot * math.exp(rate * expiry)
    errors: list[float] = []

    for strike, quoted in test:
        vol_market = implied_volatility(quoted, spot, strike, rate, expiry, option_type)
        vol_model = svi_implied_vol(math.log(strike / forward), expiry, params)
        errors.append((vol_model - vol_market) ** 2)

    test_rmse = math.sqrt(sum(errors) / len(errors))
    return train_rmse, test_rmse
