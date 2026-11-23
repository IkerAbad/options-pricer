"""Command line entry point."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from . import black76
from .american import binomial
from .black_scholes import greeks, price
from .implied_vol import implied_volatility
from .monte_carlo import price_european
from .path_dependent import asian_price, barrier_greeks, barrier_price
from .ssvi import calibrate_ssvi, is_arbitrage_free
from .surface import (
    SviParams,
    bootstrap_slice,
    calibrate,
    calibrate_surface,
    example_term_structure,
    svi_implied_vol,
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
    parser.add_argument("--json", action="store_true", help="machine-readable output")


def _emit(payload: object) -> None:
    print(json.dumps(payload, indent=2))


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

    forward_parser = sub.add_parser("forward", help="Black-76 price on a forward")
    forward_parser.add_argument("--forward", type=float, required=True)
    forward_parser.add_argument("--strike", type=float, required=True)
    forward_parser.add_argument("--rate", type=float, default=0.0)
    forward_parser.add_argument("--vol", type=float, default=0.2)
    forward_parser.add_argument("--expiry", type=float, required=True)
    forward_parser.add_argument("--type", choices=["call", "put"], default="call")
    forward_parser.add_argument("--json", action="store_true", help="machine-readable output")

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
    barrier_parser.add_argument("--greeks", action="store_true")

    surface_parser = sub.add_parser("surface", help="calibrate a synthetic SVI smile")
    surface_parser.add_argument("--spot", type=float, default=100.0)
    surface_parser.add_argument("--rate", type=float, default=0.03)
    surface_parser.add_argument("--expiry", type=float, default=1.0)
    surface_parser.add_argument("--noise", type=float, default=0.001)
    surface_parser.add_argument("--json", action="store_true", help="machine-readable output")
    surface_parser.add_argument(
        "--all", action="store_true", dest="full", help="calibrate four expiries"
    )

    ssvi_parser = sub.add_parser("ssvi", help="calibrate a synthetic SSVI surface")
    ssvi_parser.add_argument("--spot", type=float, default=100.0)
    ssvi_parser.add_argument("--rate", type=float, default=0.03)
    ssvi_parser.add_argument("--expiries", type=int, default=4)
    ssvi_parser.add_argument("--json", action="store_true", help="machine-readable output")

    bootstrap_parser = sub.add_parser("bootstrap", help="bootstrap intervals for SVI")
    _common(bootstrap_parser)
    bootstrap_parser.add_argument("--samples", type=int, default=100)
    bootstrap_parser.add_argument("--noise", type=float, default=0.001)
    bootstrap_parser.add_argument("--seed", type=int, default=1)

    args = parser.parse_args(argv)

    if args.command == "price":
        value = price(args.type, args.spot, args.strike, args.rate, args.vol, args.expiry)
        g = greeks(args.type, args.spot, args.strike, args.rate, args.vol, args.expiry)
        if args.json:
            _emit({"price": value, **asdict(g)})
            return 0
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
        mc_result = price_european(
            args.type,
            args.spot,
            args.strike,
            args.rate,
            args.vol,
            args.expiry,
            paths=args.paths,
            seed=args.seed,
        )
        if args.json:
            _emit(asdict(mc_result))
            return 0
        print(f"price  {mc_result.price:.6f}")
        print(f"stderr {mc_result.standard_error:.6f}")
        print(f"95% ci [{mc_result.ci_low:.6f}, {mc_result.ci_high:.6f}]")
        print(f"paths  {mc_result.paths}")
        return 0

    if args.command == "iv":
        vol = implied_volatility(
            args.quoted, args.spot, args.strike, args.rate, args.expiry, args.type
        )
        if args.json:
            _emit({"implied_vol": vol})
            return 0
        print(f"implied vol  {vol:.6f}")
        return 0

    if args.command == "forward":
        value = black76.price(
            args.type, args.forward, args.strike, args.rate, args.vol, args.expiry
        )
        fg = black76.greeks(args.type, args.forward, args.strike, args.rate, args.vol, args.expiry)
        if args.json:
            _emit({"price": value, **asdict(fg)})
            return 0
        print(f"price  {value:.6f}")
        print(f"delta  {fg.delta:.6f}")
        print(f"gamma  {fg.gamma:.6f}")
        print(f"vega   {fg.vega:.6f}")
        return 0

    if args.command == "american":
        american_result = binomial(
            args.type,
            args.spot,
            args.strike,
            args.rate,
            args.vol,
            args.expiry,
            steps=args.steps,
            dividend_yield=args.dividend,
        )
        if args.json:
            _emit(asdict(american_result))
            return 0
        print(f"american  {american_result.american:.6f}")
        print(f"european  {american_result.european:.6f}")
        print(f"premium   {american_result.premium:.6f}")
        print(f"steps     {american_result.steps}")
        return 0

    if args.command == "asian":
        asian_result = asian_price(
            args.type,
            args.spot,
            args.strike,
            args.rate,
            args.vol,
            args.expiry,
            steps=args.steps,
            paths=args.paths,
            seed=args.seed,
        )
        if args.json:
            _emit(asdict(asian_result))
            return 0
        print(f"price  {asian_result.price:.6f}")
        print(f"stderr {asian_result.standard_error:.6f}")
        print(f"95% ci [{asian_result.ci_low:.6f}, {asian_result.ci_high:.6f}]")
        print(f"paths  {asian_result.paths}  steps {asian_result.steps}")
        return 0

    if args.command == "barrier":
        if args.greeks:
            values = barrier_greeks(
                args.type,
                args.spot,
                args.strike,
                args.rate,
                args.vol,
                args.expiry,
                barrier=args.barrier,
                kind=args.kind,
                steps=args.steps,
                paths=args.paths,
                seed=args.seed,
            )
            if args.json:
                _emit({"kind": args.kind, "barrier": args.barrier, **asdict(values)})
                return 0
            print(f"price  {values.price:.6f}")
            print(f"delta  {values.delta:.6f}")
            print(f"vega   {values.vega:.6f}")
            print(f"theta  {values.theta:.6f}")
            print(f"kind   {args.kind} at {args.barrier}")
            return 0

        barrier_result = barrier_price(
            args.type,
            args.spot,
            args.strike,
            args.rate,
            args.vol,
            args.expiry,
            barrier=args.barrier,
            kind=args.kind,
            steps=args.steps,
            paths=args.paths,
            seed=args.seed,
        )
        if args.json:
            _emit({"kind": args.kind, "barrier": args.barrier, **asdict(barrier_result)})
            return 0
        print(f"price  {barrier_result.price:.6f}")
        print(f"stderr {barrier_result.standard_error:.6f}")
        print(f"95% ci [{barrier_result.ci_low:.6f}, {barrier_result.ci_high:.6f}]")
        print(f"kind   {args.kind} at {args.barrier}")
        return 0

    if args.command == "ssvi":
        structure = example_term_structure()
        expiries = list(structure)[: args.expiries]
        ks_grid = [index * 0.05 - 0.4 for index in range(17)]
        vols_by_expiry = [
            [svi_implied_vol(k, expiry, structure[expiry]) for k in ks_grid] for expiry in expiries
        ]
        params, rmse, thetas = calibrate_ssvi(expiries, [ks_grid for _ in expiries], vols_by_expiry)

        if args.json:
            _emit(
                {
                    **params.to_dict(),
                    "rmse": rmse,
                    "thetas": thetas,
                    "expiries": expiries,
                    "arbitrage_free": is_arbitrage_free(params),
                }
            )
            return 0

        print(f"rho    {params.rho:.6f}")
        print(f"eta    {params.eta:.6f}")
        print(f"gamma  {params.gamma:.6f}")
        print(f"rmse   {rmse:.6f}")
        print(f"arbitrage free: {is_arbitrage_free(params)}")
        return 0

    if args.command == "bootstrap":
        strikes = [80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]
        truth = SviParams(a=0.02, b=0.15, rho=-0.4, m=-0.05, sigma=0.15)
        prices = synthetic_market(
            args.spot, args.rate, args.expiry, strikes, truth, noise=args.noise
        )
        result = bootstrap_slice(
            args.spot,
            args.rate,
            args.expiry,
            strikes,
            prices,
            samples=args.samples,
            seed=args.seed,
        )

        if args.json:
            _emit(asdict(result))
            return 0

        print(f"samples {result.samples}")
        for name in ("a", "b", "rho", "m", "sigma"):
            print(f"{name:6s} [{result.lower[name]:+.6f}, {result.upper[name]:+.6f}]")
        print(f"rmse   [{result.rmse_low:.6f}, {result.rmse_high:.6f}]")
        return 0

    strikes = [80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]
    truth = SviParams(a=0.02, b=0.15, rho=-0.4, m=-0.05, sigma=0.15)

    if args.full:
        structure = example_term_structure()
        expiries = list(structure)
        surface_params = [structure[expiry] for expiry in expiries]
        quotes = synthetic_surface(
            args.spot, args.rate, expiries, strikes, surface_params, noise=args.noise
        )
        rows = calibrate_surface(args.spot, args.rate, expiries, strikes, quotes)
        if args.json:
            _emit(
                [
                    {"expiry": expiry, **fitted.to_dict(), "rmse": rmse}
                    for expiry, fitted, rmse in rows
                ]
            )
            return 0
        print("expiry        a        b      rho        m    sigma     rmse")
        for expiry, fitted, rmse in rows:
            print(
                f"{expiry:6.2f}  {fitted.a:7.4f}  {fitted.b:6.4f}  "
                f"{fitted.rho:6.3f}  {fitted.m:6.3f}  {fitted.sigma:6.3f}  {rmse:.6f}"
            )
        return 0

    prices = synthetic_market(args.spot, args.rate, args.expiry, strikes, truth, noise=args.noise)
    fitted, rmse = calibrate(args.spot, args.rate, args.expiry, strikes, prices)
    if args.json:
        _emit({**fitted.to_dict(), "rmse": rmse})
        return 0
    print(f"a      {fitted.a:.6f}")
    print(f"b      {fitted.b:.6f}")
    print(f"rho    {fitted.rho:.6f}")
    print(f"m      {fitted.m:.6f}")
    print(f"sigma  {fitted.sigma:.6f}")
    print(f"rmse   {rmse:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
