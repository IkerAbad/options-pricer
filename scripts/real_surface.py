"""Render the real BTC implied volatility surface from the versioned snapshot.

Usage:
    python scripts/real_surface.py
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from options_pricer.real_data import Slice, build_slice, load_chain
from options_pricer.surface import SviParams, calibrate_from_vols, svi_implied_vol

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "binance_btc_options_2026-11-22.csv"
DOCS = ROOT / "docs"

RED = "#c62828"
BLUE = "#1f4e79"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, default=DOCS / "real_surface.png")
    args = parser.parse_args()

    quotes = load_chain(args.input)
    by_expiry: dict[str, list] = defaultdict(list)
    for quote in quotes:
        by_expiry[quote.expiry].append(quote)

    ordered = sorted(by_expiry.items(), key=lambda item: item[1][0].days)

    slices: list[tuple[Slice, SviParams, float]] = []
    previous: SviParams | None = None

    for _, group in ordered:
        current = build_slice(group)
        if len(current.vols) < 5:
            continue
        params, rmse = calibrate_from_vols(
            current.years,
            current.log_moneyness,
            current.vols,
            initial=previous,
            floor=previous,
            hard_calendar=True,
        )
        previous = params
        slices.append((current, params, rmse))

    if len(slices) < 2:
        raise SystemExit("at least two calibrated expiries are needed for a surface")

    fig = plt.figure(figsize=(8.6, 5.6), dpi=140)
    ax = fig.add_subplot(111, projection="3d")

    for current, params, _ in slices:
        grid = np.linspace(-0.7, 0.7, 120)
        curve = [svi_implied_vol(float(k), current.years, params) for k in grid]
        ax.plot(grid, [current.years] * len(grid), curve, color=BLUE, linewidth=1.8)
        ax.scatter(
            current.log_moneyness,
            [current.years] * len(current.log_moneyness),
            current.vols,
            color=RED,
            s=8,
            depthshade=False,
            label="market quotes",
        )

    ax.set_xlabel("log-moneyness")
    ax.set_ylabel("expiry (years)")
    ax.set_zlabel("implied volatility")
    ax.set_title("BTC implied volatility slices, 22/11/2026")
    ax.view_init(elev=24, azim=-130)
    fig.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output)
    plt.close(fig)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
