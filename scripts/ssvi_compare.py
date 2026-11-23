"""Compare SSVI against one SVI slice per expiry on the real BTC snapshot.

Usage:
    python scripts/ssvi_compare.py
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from options_pricer.real_data import Quote, build_slice, load_chain
from options_pricer.ssvi import calibrate_ssvi, is_arbitrage_free, total_variance
from options_pricer.surface import calibrate_from_vols

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "binance_btc_options_2026-11-22.csv"


def main() -> None:
    quotes = load_chain(DATA)
    by_expiry: dict[str, list[Quote]] = defaultdict(list)
    for quote in quotes:
        by_expiry[quote.expiry].append(quote)

    ordered = sorted(by_expiry.items(), key=lambda item: item[1][0].days)
    slices = [build_slice(group) for _, group in ordered]

    expiries = [current.years for current in slices]
    ks = [current.log_moneyness for current in slices]
    vols = [current.vols for current in slices]

    params, rmse, thetas = calibrate_ssvi(expiries, ks, vols)
    print(f"SSVI rho {params.rho:.4f}  eta {params.eta:.4f}  gamma {params.gamma:.4f}")
    print(f"SSVI arbitrage free: {is_arbitrage_free(params)}")
    print(f"SSVI global RMSE: {rmse:.6f}")
    print()
    print("expiry        theta     SVI rmse    SSVI rmse")
    for current, theta in zip(slices, thetas, strict=True):
        _, svi_rmse = calibrate_from_vols(
            current.years, current.log_moneyness, current.vols, ridge=1e-2
        )
        errors = [
            (math.sqrt(max(total_variance(k, theta, params) / current.years, 1e-12)) - vol) ** 2
            for k, vol in zip(current.log_moneyness, current.vols, strict=True)
        ]
        ssvi_rmse = math.sqrt(sum(errors) / len(errors))
        print(f"{current.expiry}  {theta:.6f}   {svi_rmse:.6f}   {ssvi_rmse:.6f}")


if __name__ == "__main__":
    main()
