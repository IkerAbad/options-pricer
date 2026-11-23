"""Calibrate SVI on the five reconstructed days and plot the evolution.

Usage:
    python scripts/calibrate_history.py
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from options_pricer.real_data import Quote, Slice, build_slice, load_history_day
from options_pricer.surface import SviParams, calibrate_from_vols, svi_implied_vol

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "history"
DOCS = ROOT / "docs"
TARGET_EXPIRY = "2026-12-25"

BLUE = "#1f4e79"
RED = "#c62828"
GRID = "#e2e2e2"


def calibrate_day(
    quotes: list[Quote],
) -> list[tuple[str, Slice, SviParams, float]]:
    by_expiry: dict[str, list[Quote]] = defaultdict(list)
    for quote in quotes:
        by_expiry[quote.expiry].append(quote)

    ordered = sorted(by_expiry.items(), key=lambda item: item[1][0].days)
    previous: SviParams | None = None
    results: list[tuple[str, Slice, SviParams, float]] = []

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
            weights=current.weights,
        )
        previous = params
        results.append((expiry, current, params, rmse))

    return results


def main() -> None:
    days = []
    for path in sorted(HISTORY.glob("binance_btc_options_*.csv")):
        day, quotes = load_history_day(path)
        results = calibrate_day(quotes)
        days.append((day, results))
        print(f"{day}: {len(results)} expiries")

    rows = []
    for day, results in days:
        for expiry, current, params, rmse in results:
            rows.append(
                {
                    "date": day,
                    "expiry": expiry,
                    "days": f"{current.years * 365.0:.1f}",
                    "forward": f"{current.forward:.2f}",
                    "quotes": len(current.vols),
                    "a": params.a,
                    "b": params.b,
                    "rho": params.rho,
                    "m": params.m,
                    "sigma": params.sigma,
                    "rmse": rmse,
                }
            )

    table = DOCS / "history_calibration.csv"
    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    target = [
        (day, next(result for result in results if result[0] == TARGET_EXPIRY))
        for day, results in days
        if any(result[0] == TARGET_EXPIRY for result in results)
    ]

    fig, (left, right) = plt.subplots(1, 2, figsize=(11.0, 4.4), dpi=140)
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(target)))

    for color, (day, (_, current, params, _)) in zip(colors, target, strict=True):
        k_grid = np.linspace(-0.7, 0.7, 200)
        strikes = current.forward * np.exp(k_grid)
        curve = [svi_implied_vol(float(k), current.years, params) for k in k_grid]
        left.plot(strikes, curve, color=color, linewidth=1.3, label=day)

    left.set_xlabel("strike (USDT)")
    left.set_ylabel("implied volatility")
    left.set_title(f"SVI smiles, expiry {TARGET_EXPIRY}")
    left.grid(color=GRID, linewidth=0.6)
    left.legend(frameon=False, fontsize=7)

    names = ("a", "b", "rho", "m", "sigma")
    day_labels = [day for day, _ in target]
    for name in names:
        values = [getattr(params, name) for _, (_, _, params, _) in target]
        right.plot(day_labels, values, marker="o", linewidth=1.2, label=name)

    right.set_title("SVI parameters over time")
    right.set_ylabel("value")
    right.grid(color=GRID, linewidth=0.6)
    right.legend(frameon=False, fontsize=7)
    right.tick_params(axis="x", rotation=25, labelsize=7)

    for axis in (left, right):
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)

    fig.tight_layout()
    fig.savefig(DOCS / "history_calibration.png")
    plt.close(fig)

    print(f"wrote {table} and {DOCS / 'history_calibration.png'}")
    print()
    print("date        a         b       rho        m      sigma     rmse")
    for day, (_, _, params, rmse) in target:
        print(
            f"{day}  {params.a:+.4f}  {params.b:+.4f}  {params.rho:+.3f}  "
            f"{params.m:+.3f}  {params.sigma:.3f}  {rmse:.6f}"
        )


if __name__ == "__main__":
    main()
