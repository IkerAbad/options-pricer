"""Time the SVI calibration on the real BTC snapshot.

Usage:
    python scripts/bench_calibration.py
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from pathlib import Path

from options_pricer.real_data import build_slice, load_chain
from options_pricer.surface import calibrate_from_vols

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "binance_btc_options_2026-11-22.csv"
REPEATS = 10


def main() -> None:
    quotes = load_chain(DATA)
    by_expiry: dict[str, list] = defaultdict(list)
    for quote in quotes:
        by_expiry[quote.expiry].append(quote)

    ordered = sorted(by_expiry.values(), key=lambda group: group[0].days)
    first = build_slice(ordered[0])
    second = build_slice(ordered[1])

    short, _ = calibrate_from_vols(first.years, first.log_moneyness, first.vols)

    print("method   median ms   min ms   max ms")
    for label, hard in (("soft", False), ("hard", True)):
        timings: list[float] = []
        for _ in range(REPEATS):
            start = time.perf_counter()
            calibrate_from_vols(
                second.years,
                second.log_moneyness,
                second.vols,
                initial=short,
                floor=short,
                hard_calendar=hard,
            )
            timings.append((time.perf_counter() - start) * 1000.0)

        print(
            f"{label:6s}  {statistics.median(timings):9.2f}  "
            f"{min(timings):7.2f}  {max(timings):7.2f}"
        )


if __name__ == "__main__":
    main()
