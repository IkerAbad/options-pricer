"""Time the Black-Scholes engine.

Usage:
    python scripts/bench_black_scholes.py
"""

from __future__ import annotations

import statistics
import time

from options_pricer.black_scholes import price

PRICES = 100_000
REPEATS = 5


def main() -> None:
    timings: list[float] = []

    for _ in range(REPEATS):
        start = time.perf_counter()
        total = 0.0
        for index in range(PRICES):
            strike = 80.0 + (index % 40)
            total += price("call", 100.0, strike, 0.05, 0.20, 1.0)
        timings.append(time.perf_counter() - start)

    median = statistics.median(timings)
    print(f"{PRICES} prices in {median * 1000.0:.1f} ms")
    print(f"{PRICES / median:.0f} prices/s")
    print(f"checksum {total:.6f}")


if __name__ == "__main__":
    main()
