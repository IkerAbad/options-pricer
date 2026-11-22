"""Generate the two figures used in the README."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from options_pricer.american import binomial
from options_pricer.black_scholes import call_price
from options_pricer.implied_vol import implied_volatility
from options_pricer.monte_carlo import price_european
from options_pricer.path_dependent import barrier_price
from options_pricer.surface import (
    SviParams,
    calibrate,
    calibrate_surface,
    example_term_structure,
    svi_implied_vol,
    synthetic_market,
    synthetic_surface,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0

BLUE = "#1f4e79"
RED = "#c62828"
GRID = "#e2e2e2"


def convergence(path: Path) -> None:
    counts = [1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000, 200_000, 500_000]
    prices = []
    errors = []

    for count in counts:
        result = price_european(
            "call", SPOT, STRIKE, RATE, VOL, EXPIRY, paths=count, seed=7
        )
        prices.append(result.price)
        errors.append(1.96 * result.standard_error)

    analytic = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)

    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=140)
    ax.errorbar(
        counts,
        prices,
        yerr=errors,
        fmt="o",
        color=BLUE,
        capsize=3,
        markersize=4,
        label="Monte Carlo, 95% interval",
    )
    ax.axhline(
        analytic, color=RED, linewidth=1.2, label=f"Black-Scholes {analytic:.4f}"
    )
    ax.set_xscale("log")
    ax.set_xlabel("paths")
    ax.set_ylabel("call price")
    ax.set_title("Monte Carlo convergence, S = K = 100, r = 5%, vol = 20%, T = 1")
    ax.grid(color=GRID, linewidth=0.6)
    ax.legend(frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def smile(path: Path) -> None:
    strikes = [80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]
    truth = SviParams(a=0.02, b=0.15, rho=-0.4, m=-0.05, sigma=0.15)
    rate = 0.03
    expiry = 1.0

    quotes = synthetic_market(
        SPOT, rate, expiry, strikes, truth, noise=0.001, seed=1
    )
    fitted, rmse = calibrate(SPOT, rate, expiry, strikes, quotes)

    market_vols = [
        implied_volatility(quoted, SPOT, strike, rate, expiry, "call")
        for strike, quoted in zip(strikes, quotes)
    ]

    forward = SPOT * math.exp(rate * expiry)
    grid = [70.0 + 0.5 * i for i in range(121)]
    curve = [svi_implied_vol(math.log(strike / forward), expiry, fitted) for strike in grid]

    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=140)
    ax.plot(grid, curve, color=BLUE, linewidth=1.4, label="SVI fit")
    ax.scatter(
        strikes,
        market_vols,
        color=RED,
        zorder=3,
        s=22,
        label="quoted implied volatility",
    )
    ax.set_xlabel("strike")
    ax.set_ylabel("implied volatility")
    ax.set_title(f"Volatility smile, SVI calibration, RMSE {rmse * 100:.3f} vol points")
    ax.grid(color=GRID, linewidth=0.6)
    ax.legend(frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def surface_3d(path: Path) -> None:
    spot = 100.0
    rate = 0.03
    strikes = [75.0 + 5.0 * i for i in range(11)]
    structure = example_term_structure()
    expiries = sorted(structure)
    params = [structure[expiry] for expiry in expiries]

    quotes = synthetic_surface(
        spot, rate, expiries, strikes, params, noise=0.001, seed=1
    )
    fits = calibrate_surface(spot, rate, expiries, strikes, quotes)

    log_expiries = np.log(np.array(expiries))
    names = ("a", "b", "rho", "m", "sigma")
    fitted_values = {
        name: np.array([getattr(fitted, name) for _, fitted, _ in fits]) for name in names
    }

    expiry_grid = np.linspace(min(expiries), max(expiries), 40)
    strike_grid = np.linspace(min(strikes), max(strikes), 41)
    strike_mesh, expiry_mesh = np.meshgrid(strike_grid, expiry_grid)
    vol_mesh = np.zeros_like(strike_mesh)

    for i, expiry in enumerate(expiry_grid):
        interpolated = {
            name: float(np.interp(np.log(expiry), log_expiries, fitted_values[name]))
            for name in names
        }
        candidate = SviParams(**interpolated)
        forward = spot * math.exp(rate * expiry)
        for j, strike in enumerate(strike_grid):
            vol_mesh[i, j] = svi_implied_vol(
                math.log(float(strike) / forward), float(expiry), candidate
            )

    point_strike: list[float] = []
    point_expiry: list[float] = []
    point_vol: list[float] = []
    for expiry, series in zip(expiries, quotes):
        for strike, quoted in zip(strikes, series):
            point_strike.append(strike)
            point_expiry.append(expiry)
            point_vol.append(
                implied_volatility(quoted, spot, strike, rate, expiry, "call")
            )

    fig = plt.figure(figsize=(8.6, 5.6), dpi=140)
    ax = fig.add_subplot(111, projection="3d")
    surface = ax.plot_surface(
        strike_mesh,
        expiry_mesh,
        vol_mesh,
        cmap="viridis",
        alpha=0.78,
        linewidth=0,
        antialiased=True,
    )
    ax.scatter(
        point_strike,
        point_expiry,
        point_vol,
        color=RED,
        s=12,
        depthshade=False,
        label="quoted implied volatility",
    )
    ax.set_xlabel("strike")
    ax.set_ylabel("expiry (years)")
    ax.set_zlabel("implied volatility")
    ax.set_title("Implied volatility surface, SVI slices interpolated in log time")
    ax.view_init(elev=24, azim=-130)
    ax.legend(frameon=False, loc="upper left")
    fig.colorbar(surface, shrink=0.6, pad=0.1, label="implied volatility")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def early_exercise(path: Path) -> None:
    strike = 100.0
    spots = np.linspace(60.0, 140.0, 41)
    american: list[float] = []
    european: list[float] = []

    for spot in spots:
        result = binomial(
            "put", float(spot), strike, 0.05, 0.20, 1.0, steps=400
        )
        american.append(result.american)
        european.append(result.european)

    premium = np.array(american) - np.array(european)

    fig, (left, right) = plt.subplots(1, 2, figsize=(10.0, 4.0), dpi=140)

    left.plot(spots, american, color=BLUE, linewidth=1.4, label="American put")
    left.plot(spots, european, color=RED, linewidth=1.2, linestyle="--", label="European put")
    left.set_xlabel("spot")
    left.set_ylabel("price")
    left.set_title("Put price, K = 100, r = 5%, vol = 20%, T = 1")
    left.legend(frameon=False)
    left.grid(color=GRID, linewidth=0.6)

    right.plot(spots, premium, color=BLUE, linewidth=1.4)
    right.set_xlabel("spot")
    right.set_ylabel("early exercise premium")
    right.set_title("Value of the right to exercise early")

    for axis in (left, right):
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)

    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def barrier_curve(path: Path) -> None:
    barriers = np.linspace(105.0, 200.0, 30)
    prices = [
        barrier_price(
            "call", 100.0, 100.0, 0.05, 0.20, 1.0,
            barrier=float(level), kind="up-and-out",
            steps=100, paths=20_000, seed=5,
        ).price
        for level in barriers
    ]
    european = call_price(100.0, 100.0, 0.05, 0.20, 1.0)

    fig, ax = plt.subplots(figsize=(7.6, 4.2), dpi=140)
    ax.plot(barriers, prices, color=BLUE, linewidth=1.4, label="up-and-out call")
    ax.axhline(
        european, color=RED, linewidth=1.2, linestyle="--",
        label=f"European call {european:.4f}",
    )
    ax.set_xlabel("barrier level")
    ax.set_ylabel("price")
    ax.set_title("Up-and-out call, S = K = 100, r = 5%, vol = 20%, T = 1")
    ax.grid(color=GRID, linewidth=0.6)
    ax.legend(frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    convergence(DOCS / "monte_carlo_convergence.png")
    smile(DOCS / "volatility_smile.png")
    surface_3d(DOCS / "volatility_surface.png")
    early_exercise(DOCS / "early_exercise.png")
    barrier_curve(DOCS / "barrier_curve.png")
    print(f"wrote figures to {DOCS}")


if __name__ == "__main__":
    main()
