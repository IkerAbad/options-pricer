"""Command line entry point."""

from __future__ import annotations

import argparse
import math

from .american import binomial
from .black_scholes import greeks, price
from .implied_vol import implied_volatility
from .monte_carlo import price_european
from .path_dependent import asian_price, barrier_price
from .surface import (
    SviParams,
    calibrate,
    calibrate_surface,
    example_term_structure,
    synthetic_market,
    synthetic_surface,
)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--spot", type=float, required=True)
    parser.add_argument("--strike", type=float, required=True)
    parser.add_argument("--rate", type=float, default=0.0)
    parser.add_argument("--vol", type=float, default=0.2)
    parser.add_argument("--expiry", type=float, required=True)
    parser.add_argument("--type", choices=["call", "put"], default="call")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="options-pricer")
    sub = parser.add_subparsers(dest="command", required=True)

    price_parser = sub.add_parser("price", help="Black-Scholes price and Greeks")
    _common(price_parser)

    mc_parser = sub.add_parser("mc", help="Monte Carlo price")
    _common(mc_parser)
    mc_parser.add_argument("--paths", type=int, default=1_000_000)
    mc_parser.add_argument("--seed", type=int, default=42)

    iv_parser = sub.add_parser("iv", help="implied volatility from a quoted price")
    _common(iv_parser)
    iv_parser.add_argument("--price", type=float, required=True, dest="quoted")

    american_parser = sub.add_parser("american", help="American price by binomial tree")
    _common(american_parser)
    american_parser.add_argument("--steps", type=int, default=1_000)
    american_parser.add_argument("--dividend", type=float, default=0.0)

    asian_parser = sub.add_parser("asian", help="arithmetic-average Asian option")
    _common(asian_parser)
    asian_parser.add_argument("--steps", type=int, default=100)
    asian_parser.add_argument("--paths", type=int, default=100_000)
    asian_parser.add_argument("--seed", type=int, default=42)

    barrier_parser = sub.add_parser("barrier", help="barrier option with discrete monitoring")
    _common(barrier_parser)
    barrier_parser.add_argument("--barrier", type=float, required=True)
    barrier_parser.add_argument(
        "--kind",
        choices=["up-and-out", "up-and-in", "down-and-out", "down-and-in"],
        default="up-and-out",
    )
    barrier_parser.add_argument("--steps", type=int, default=100)
    barrier_parser.add_argument("--paths", type=int, default=100_000)
    barrier_parser.add_argument("--seed", type=int, default=42)

    surface_parser = sub.add_parser("surface", help="calibrate a synthetic SVI smile")
    surface_parser.add_argument("--spot", type=float, default=100.0)
    surface_parser.add_argument("--rate", type=float, default=0.03)
    surface_parser.add_argument("--expiry", type=float, default=1.0)
    surface_parser.add_argument("--noise", type=float, default=0.001)
    surface_parser.add_argument(
        "--all", action="store_true", dest="full", help="calibrate four expiries"
    )

    args = parser.parse_args(argv)

    if args.command == "price":
        value = price(args.type, args.spot, args.strike, args.rate, args.vol, args.expiry)
        g = greeks(args.type, args.spot, args.strike, args.rate, args.vol, args.expiry)
        print(f"price  {value:.6f}")
        print(f"delta  {g.delta:.6f}")
        print(f"gamma  {g.gamma:.6f}")
        print(f"vega   {g.vega:.6f}")
        print(f"theta  {g.theta:.6f}")
        print(f"rho    {g.rho:.6f}")
        print(f"vanna  {g.vanna:.6f}")
        print(f"volga  {g.volga:.6f}")
        print(f"charm  {g.charm:.6f}")
        return 0

    if args.command == "mc":
        result = price_european(
            args.type,
            args.spot,
            args.strike,
            args.rate,
            args.vol,
            args.expiry,
            paths=args.paths,
            seed=args.seed,
        )
        print(f"price  {result.price:.6f}")
        print(f"stderr {result.standard_error:.6f}")
        print(f"95% ci [{result.ci_low:.6f}, {result.ci_high:.6f}]")
        print(f"paths  {result.paths}")
        return 0

    if args.command == "iv":
        vol = implied_volatility(
            args.quoted, args.spot, args.strike, args.rate, args.expiry, args.type
        )
        print(f"implied vol  {vol:.6f}")
        return 0

    if args.command == "american":
        result = binomial(
            args.type,
            args.spot,
            args.strike,
            args.rate,
            args.vol,
            args.expiry,
            steps=args.steps,
            dividend_yield=args.dividend,
        )
        print(f"american  {result.american:.6f}")
        print(f"european  {result.european:.6f}")
        print(f"premium   {result.premium:.6f}")
        print(f"steps     {result.steps}")
        return 0

    if args.command == "asian":
        result = asian_price(
            args.type, args.spot, args.strike, args.rate, args.vol, args.expiry,
            steps=args.steps, paths=args.paths, seed=args.seed,
        )
        print(f"price  {result.price:.6f}")
        print(f"stderr {result.standard_error:.6f}")
        print(f"95% ci [{result.ci_low:.6f}, {result.ci_high:.6f}]")
        print(f"paths  {result.paths}  steps {result.steps}")
        return 0

    if args.command == "barrier":
        result = barrier_price(
            args.type, args.spot, args.strike, args.rate, args.vol, args.expiry,
            barrier=args.barrier, kind=args.kind, steps=args.steps,
            paths=args.paths, seed=args.seed,
        )
        print(f"price  {result.price:.6f}")
        print(f"stderr {result.standard_error:.6f}")
        print(f"95% ci [{result.ci_low:.6f}, {result.ci_high:.6f}]")
        print(f"kind   {args.kind} at {args.barrier}")
        return 0

    strikes = [80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]
    truth = SviParams(a=0.02, b=0.15, rho=-0.4, m=-0.05, sigma=0.15)

    if args.full:
        structure = example_term_structure()
        expiries = list(structure)
        params = [structure[expiry] for expiry in expiries]
        quotes = synthetic_surface(
            args.spot, args.rate, expiries, strikes, params, noise=args.noise
        )
        rows = calibrate_surface(args.spot, args.rate, expiries, strikes, quotes)
        print("expiry        a        b      rho        m    sigma     rmse")
        for expiry, fitted, rmse in rows:
            print(
                f"{expiry:6.2f}  {fitted.a:7.4f}  {fitted.b:6.4f}  "
                f"{fitted.rho:6.3f}  {fitted.m:6.3f}  {fitted.sigma:6.3f}  {rmse:.6f}"
            )
        return 0

    prices = synthetic_market(
        args.spot, args.rate, args.expiry, strikes, truth, noise=args.noise
    )
    fitted, rmse = calibrate(args.spot, args.rate, args.expiry, strikes, prices)
    print(f"a      {fitted.a:.6f}")
    print(f"b      {fitted.b:.6f}")
    print(f"rho    {fitted.rho:.6f}")
    print(f"m      {fitted.m:.6f}")
    print(f"sigma  {fitted.sigma:.6f}")
    print(f"rmse   {rmse:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
