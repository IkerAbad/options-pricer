"""Generate the two figures used in the README."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from options_pricer.black_scholes import call_price
from options_pricer.implied_vol import implied_volatility
from options_pricer.monte_carlo import price_european
from options_pricer.surface import (
    SviParams,
    calibrate,
    svi_implied_vol,
    synthetic_market,
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


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    convergence(DOCS / "monte_carlo_convergence.png")
    smile(DOCS / "volatility_smile.png")
    print(f"wrote figures to {DOCS}")


if __name__ == "__main__":
    main()
