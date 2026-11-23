"""Time the binomial tree and the path-dependent engines.

Usage:
    python scripts/bench_paths.py
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable

from options_pricer.american import binomial
from options_pricer.path_dependent import asian_price, barrier_price

REPEATS = 5


def bench(label: str, call: Callable[[], object]) -> None:
    timings: list[float] = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        call()
        timings.append(time.perf_counter() - start)
    median = statistics.median(timings)
    print(f"{label:28s} {median * 1000:9.1f} ms")


def main() -> None:
    bench(
        "binomial, 1000 steps",
        lambda: binomial("put", 100.0, 100.0, 0.05, 0.20, 1.0, steps=1_000),
    )
    bench(
        "asian, 100k paths, 100 steps",
        lambda: asian_price("call", 100.0, 100.0, 0.05, 0.20, 1.0, steps=100, paths=100_000),
    )
    bench(
        "barrier, 100k paths, 100 steps",
        lambda: barrier_price(
            "call",
            100.0,
            100.0,
            0.05,
            0.20,
            1.0,
            barrier=120.0,
            steps=100,
            paths=100_000,
        ),
    )


if __name__ == "__main__":
    main()
