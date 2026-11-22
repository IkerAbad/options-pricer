"""Command line entry point."""

from __future__ import annotations

import argparse
import math

from .black_scholes import greeks, price
from .implied_vol import implied_volatility
from .monte_carlo import price_european
from .surface import SviParams, calibrate, synthetic_market


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

    surface_parser = sub.add_parser("surface", help="calibrate a synthetic SVI smile")
    surface_parser.add_argument("--spot", type=float, default=100.0)
    surface_parser.add_argument("--rate", type=float, default=0.03)
    surface_parser.add_argument("--expiry", type=float, default=1.0)
    surface_parser.add_argument("--noise", type=float, default=0.001)

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

    strikes = [80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]
    truth = SviParams(a=0.02, b=0.15, rho=-0.4, m=-0.05, sigma=0.15)
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
