"""Write the reference values used by the regression test.

Run only when a numerical result changes on purpose:

    python scripts/write_reference.py
"""

from __future__ import annotations

import json
from pathlib import Path

from options_pricer import black76
from options_pricer.american import binomial
from options_pricer.black_scholes import call_price, greeks, put_price
from options_pricer.implied_vol import implied_volatility
from options_pricer.path_dependent import asian_price, barrier_price
from options_pricer.path_greeks import (
    asian_greeks_fd,
    asian_greeks_lr,
    barrier_greeks_fd,
    barrier_greeks_lr,
)
from options_pricer.surface import SviParams, calibrate, synthetic_market

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "tests" / "data" / "reference_values.json"

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def main() -> None:
    call = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    put = put_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    greek_values = greeks("call", SPOT, STRIKE, RATE, VOL, EXPIRY)

    forward = SPOT * 2.718281828459045**RATE
    truth = SviParams(a=0.02, b=0.15, rho=-0.4, m=-0.05, sigma=0.15)
    strikes = [80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]
    quotes = synthetic_market(SPOT, 0.03, EXPIRY, strikes, truth, noise=0.001, seed=1)
    _, svi_rmse = calibrate(SPOT, 0.03, EXPIRY, strikes, quotes)

    asian_fd = asian_greeks_fd(
        "call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=50, paths=200_000, seed=7
    )
    asian_lr = asian_greeks_lr(
        "call", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=50, paths=1_000_000, seed=7
    )
    barrier_fd = barrier_greeks_fd(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        steps=50,
        paths=200_000,
        seed=7,
    )
    barrier_lr = barrier_greeks_lr(
        "call",
        SPOT,
        STRIKE,
        RATE,
        VOL,
        EXPIRY,
        barrier=120.0,
        steps=50,
        paths=1_000_000,
        seed=7,
    )

    values = {
        "black_scholes_call": call,
        "black_scholes_put": put,
        "delta": greek_values.delta,
        "gamma": greek_values.gamma,
        "vega": greek_values.vega,
        "theta": greek_values.theta,
        "rho": greek_values.rho,
        "vanna": greek_values.vanna,
        "volga": greek_values.volga,
        "charm": greek_values.charm,
        "black76_call": black76.price("call", forward, STRIKE, RATE, VOL, EXPIRY),
        "american_put": binomial("put", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=1_000).american,
        "implied_vol": implied_volatility(call, SPOT, STRIKE, RATE, EXPIRY, "call"),
        "asian_call": asian_price(
            "call",
            SPOT,
            STRIKE,
            RATE,
            VOL,
            EXPIRY,
            steps=50,
            paths=20_000,
            seed=7,
        ).price,
        "barrier_discrete": barrier_price(
            "call",
            SPOT,
            STRIKE,
            RATE,
            VOL,
            EXPIRY,
            barrier=120.0,
            steps=50,
            paths=20_000,
            seed=7,
        ).price,
        "barrier_continuous": barrier_price(
            "call",
            SPOT,
            STRIKE,
            RATE,
            VOL,
            EXPIRY,
            barrier=120.0,
            steps=50,
            paths=20_000,
            seed=7,
            continuous=True,
        ).price,
        "svi_rmse": svi_rmse,
        "asian_fd_delta": asian_fd.delta,
        "asian_fd_gamma": asian_fd.gamma,
        "asian_fd_vega": asian_fd.vega,
        "asian_lr_delta": asian_lr.delta,
        "asian_lr_gamma": asian_lr.gamma,
        "asian_lr_vega": asian_lr.vega,
        "barrier_fd_delta": barrier_fd.delta,
        "barrier_fd_gamma": barrier_fd.gamma,
        "barrier_fd_vega": barrier_fd.vega,
        "barrier_lr_delta": barrier_lr.delta,
        "barrier_lr_gamma": barrier_lr.gamma,
        "barrier_lr_vega": barrier_lr.vega,
    }

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(values)} values to {TARGET}")


if __name__ == "__main__":
    main()
