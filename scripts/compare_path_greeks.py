"""Compare path-dependent Greeks by finite differences and likelihood ratio.

Reference: finite differences with common random numbers at 400,000 paths.
Each method runs with 100,000 paths. Errors are relative to the reference.

Usage:
    python scripts/compare_path_greeks.py
"""

from __future__ import annotations

import time
from collections.abc import Callable

from options_pricer.path_greeks import (
    PathGreeksResult,
    asian_greeks_fd,
    asian_greeks_lr,
    barrier_greeks_fd,
    barrier_greeks_lr,
)

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0
STEPS = 100
PATHS = 100_000
LR_PATHS = 1_000_000
REFERENCE_PATHS = 400_000
SEED = 42


def relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1e-9)


def report(
    family: str,
    reference: PathGreeksResult,
    methods: dict[str, Callable[[], PathGreeksResult]],
) -> None:
    print(f"\n{family}")
    print("method            delta err   gamma err    vega err     ms")
    for name, build in methods.items():
        start = time.perf_counter()
        result = build()
        elapsed = (time.perf_counter() - start) * 1000.0
        print(
            f"{name:16s}  {relative(result.delta, reference.delta) * 100:8.2f}%  "
            f"{relative(result.gamma, reference.gamma) * 100:8.2f}%  "
            f"{relative(result.vega, reference.vega) * 100:8.2f}%  "
            f"{elapsed:7.1f}"
        )


def main() -> None:
    asian_reference = asian_greeks_fd(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        steps=STEPS,
        paths=REFERENCE_PATHS,
        seed=SEED,
    )
    barrier_reference = barrier_greeks_lr(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        steps=STEPS,
        paths=2_000_000,
        seed=SEED,
    )

    report(
        "Asian call",
        asian_reference,
        {
            "fd-crn": lambda: asian_greeks_fd(
                "call",
                SPOT,
                STRIKE,
                RATE,
                VOL,
                EXPIRY,
                steps=STEPS,
                paths=PATHS,
                seed=SEED,
            ),
            "fd-independent": lambda: asian_greeks_fd(
                "call",
                SPOT,
                STRIKE,
                RATE,
                VOL,
                EXPIRY,
                steps=STEPS,
                paths=PATHS,
                seed=SEED,
                independent=True,
            ),
            "likelihood-ratio": lambda: asian_greeks_lr(
                "call",
                SPOT,
                STRIKE,
                RATE,
                VOL,
                EXPIRY,
                steps=STEPS,
                paths=LR_PATHS,
                seed=SEED,
            ),
        },
    )

    report(
        "Up-and-out call, barrier 120",
        barrier_reference,
        {
            "fd-crn": lambda: barrier_greeks_fd(
                "call",
                SPOT,
                STRIKE,
                RATE,
                VOL,
                EXPIRY,
                barrier=120.0,
                steps=STEPS,
                paths=PATHS,
                seed=SEED,
            ),
            "fd-independent": lambda: barrier_greeks_fd(
                "call",
                SPOT,
                STRIKE,
                RATE,
                VOL,
                EXPIRY,
                barrier=120.0,
                steps=STEPS,
                paths=PATHS,
                seed=SEED,
                independent=True,
            ),
            "likelihood-ratio": lambda: barrier_greeks_lr(
                "call",
                SPOT,
                STRIKE,
                RATE,
                VOL,
                EXPIRY,
                barrier=120.0,
                steps=STEPS,
                paths=LR_PATHS,
                seed=SEED,
            ),
        },
    )

    print("\nreference values")
    for name, result in (("asian", asian_reference), ("barrier", barrier_reference)):
        print(
            f"{name:8s} price {result.price:.6f}  delta {result.delta:.6f}  "
            f"gamma {result.gamma:.6f}  vega {result.vega:.6f}"
        )


if __name__ == "__main__":
    main()
