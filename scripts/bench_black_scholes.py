"""Time the Black-Scholes engine, scalar and vectorised.

Usage:
    python scripts/bench_black_scholes.py
"""

from __future__ import annotations

import statistics
import time

import numpy as np

from options_pricer.black_scholes import price, prices

SCALAR_PRICES = 100_000
VECTOR_PRICES = 1_000_000
REPEATS = 5


def scalar_benchmark() -> tuple[float, float]:
    timings: list[float] = []
    checksum = 0.0

    for _ in range(REPEATS):
        start = time.perf_counter()
        total = 0.0
        for index in range(SCALAR_PRICES):
            strike = 80.0 + (index % 40)
            total += price("call", 100.0, strike, 0.05, 0.20, 1.0)
        timings.append(time.perf_counter() - start)
        checksum = total

    return statistics.median(timings), checksum


def vector_benchmark() -> tuple[float, float]:
    spots = np.full(VECTOR_PRICES, 100.0)
    strikes = np.linspace(80.0, 120.0, VECTOR_PRICES)
    timings: list[float] = []
    checksum = 0.0

    for _ in range(REPEATS):
        start = time.perf_counter()
        values = prices("call", spots, strikes, 0.05, 0.20, 1.0)
        timings.append(time.perf_counter() - start)
        checksum = float(values.sum())

    return statistics.median(timings), checksum


def main() -> None:
    scalar_time, scalar_sum = scalar_benchmark()
    vector_time, vector_sum = vector_benchmark()

    print(f"scalar      {SCALAR_PRICES} prices in {scalar_time * 1000:8.1f} ms")
    print(f"scalar      {SCALAR_PRICES / scalar_time:12.0f} prices/s")
    print(f"vectorised  {VECTOR_PRICES} prices in {vector_time * 1000:8.1f} ms")
    print(f"vectorised  {VECTOR_PRICES / vector_time:12.0f} prices/s")
    print(f"scalar sum  {scalar_sum:.6f}")
    print(f"vector sum  {vector_sum:.6f}")


if __name__ == "__main__":
    main()
