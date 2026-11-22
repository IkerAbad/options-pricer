"""Calibrate SVI on the Binance snapshot and draw the real volatility smile.

Usage:
    python scripts/real_smile.py
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from options_pricer.real_data import Quote, Slice, build_slice, load_chain
from options_pricer.surface import (
    SviParams,
    butterfly_share_below_zero,
    calendar_gap,
    calibrate_from_vols,
    svi_implied_vol,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "binance_btc_options_2026-11-22.csv"
DOCS = ROOT / "docs"

BLUE = "#1f4e79"
RED = "#c62828"
GRID = "#e2e2e2"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DATA)
    parser.add_argument("--label", default="BTC")
    parser.add_argument("--output", type=Path, default=DOCS / "real_smile.png")
    args = parser.parse_args()

    quotes = load_chain(args.input)

    by_expiry: dict[str, list[Quote]] = defaultdict(list)
    for quote in quotes:
        by_expiry[quote.expiry].append(quote)

    ordered = sorted(by_expiry.items(), key=lambda item: item[1][0].days)

    previous: SviParams | None = None
    fits: dict[str, tuple[Slice, SviParams, float]] = {}

    print("expiry        days    forward      quotes    rmse   butterfly")
    for expiry, group in ordered:
        current = build_slice(group)
        if len(current.vols) < 5:
            continue

        params, rmse = calibrate_from_vols(
            current.years,
            current.log_moneyness,
            current.vols,
            initial=previous,
            ridge=1e-2,
            floor=previous,
            hard_calendar=True,
        )
        previous = params
        fits[expiry] = (current, params, rmse)
        share = butterfly_share_below_zero(params, -1.0, 1.0)
        print(
            f"{expiry}  {current.years * 365.0:6.1f}  {current.forward:9.2f}  "
            f"{len(current.vols):6d}  {rmse:.6f}   {share * 100:5.1f}%"
        )

    if not fits:
        raise SystemExit("no slice could be calibrated")

    ordered_fits = [(expiry, fits[expiry][1]) for expiry, _ in ordered if expiry in fits]
    for (first, short), (second, long) in zip(ordered_fits, ordered_fits[1:], strict=False):
        gap = calendar_gap(short, long, -1.0, 1.0)
        flag = "ok" if gap >= -1e-6 else "ARBITRAGE"
        print(f"calendar {first} -> {second}: {gap:+.2e}  {flag}")

    target = ordered[0][0]
    current, params, rmse = fits[target]

    ks_grid = np.linspace(min(current.log_moneyness) - 0.05, max(current.log_moneyness) + 0.05, 300)
    curve_strikes = current.forward * np.exp(ks_grid)
    curve_vols = [svi_implied_vol(float(k), current.years, params) for k in ks_grid]

    fig, ax = plt.subplots(figsize=(7.8, 4.4), dpi=140)
    ax.plot(curve_strikes, curve_vols, color=BLUE, linewidth=1.4, label="SVI fit")
    ax.scatter(
        current.strikes,
        current.vols,
        color=RED,
        s=14,
        zorder=3,
        label="market quotes",
    )
    ax.set_xlabel("strike (USDT)")
    ax.set_ylabel("implied volatility")
    ax.set_title(
        f"{args.label} options, {target} expiry, {len(current.vols)} quotes, "
        f"RMSE {rmse * 100:.2f} vol points"
    )
    ax.grid(color=GRID, linewidth=0.6)
    ax.legend(frameon=False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output)
    plt.close(fig)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
