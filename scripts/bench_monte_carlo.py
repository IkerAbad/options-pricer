"""Time the Monte Carlo engine.

Usage:
    python scripts/bench_monte_carlo.py
"""

from __future__ import annotations

import statistics
import time

from options_pricer.monte_carlo import price_european

PATHS = 1_000_000
REPEATS = 5


def main() -> None:
    print("mode       paths       median ms      paths/s")
    for antithetic in (True, False):
        timings: list[float] = []
        for _ in range(REPEATS):
            start = time.perf_counter()
            result = price_european(
                "call",
                100.0,
                100.0,
                0.05,
                0.20,
                1.0,
                paths=PATHS,
                seed=7,
                antithetic=antithetic,
            )
            timings.append((time.perf_counter() - start) * 1000.0)

        median_ms = statistics.median(timings)
        label = "antithetic" if antithetic else "plain"
        print(
            f"{label:10s} {result.paths:9d} {median_ms:14.2f} "
            f"{result.paths / (median_ms / 1000.0):13.0f}"
        )


if __name__ == "__main__":
    main()
