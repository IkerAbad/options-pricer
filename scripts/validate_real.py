"""Out-of-sample error and bootstrap intervals on the real BTC snapshot.

Usage:
    python scripts/validate_real.py
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from options_pricer import black_scholes
from options_pricer.real_data import Quote, build_slice, load_chain
from options_pricer.surface import bootstrap_slice, out_of_sample_rmse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "binance_btc_options_2026-11-22.csv"


def main() -> None:
    quotes = load_chain(DATA)
    by_expiry: dict[str, list[Quote]] = defaultdict(list)
    for quote in quotes:
        by_expiry[quote.expiry].append(quote)

    ordered = sorted(by_expiry.items(), key=lambda item: item[1][0].days)

    print("expiry        train rmse   test rmse   a interval            b interval")
    for expiry, group in ordered:
        current = build_slice(group)
        synthetic_prices = [
            black_scholes.price("call", current.forward, strike, 0.0, vol, current.years)
            for strike, vol in zip(current.strikes, current.vols, strict=True)
        ]

        train, test = out_of_sample_rmse(
            current.forward, 0.0, current.years, current.strikes, synthetic_prices
        )
        interval = bootstrap_slice(
            current.forward,
            0.0,
            current.years,
            current.strikes,
            synthetic_prices,
            samples=100,
            seed=3,
        )

        print(
            f"{expiry}  {train:.6f}   {test:.6f}   "
            f"[{interval.lower['a']:+.4f}, {interval.upper['a']:+.4f}]   "
            f"[{interval.lower['b']:.4f}, {interval.upper['b']:.4f}]"
        )


if __name__ == "__main__":
    main()
