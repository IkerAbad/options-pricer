# Changelog

## Unreleased

- Black-76 prices, forward Greeks and implied volatility for options on a
  forward.
- JSON output in every CLI command.
- SVI parameters serialise to and from plain dictionaries.
- Benchmarks for the SVI calibration and the Monte Carlo engine.
- Branch coverage, mypy on the scripts and Python 3.14 in CI.
- 93 tests, 94 % branch coverage.

## 0.1.0

Initial release.

- Black-Scholes prices and first and second order Greeks for European options.
- Monte Carlo with antithetic variates, standard error and a 95 % interval.
- Implied volatility by Brent root finding.
- SVI calibration from prices and from implied volatilities, with a soft or a
  hard calendar constraint and butterfly diagnostics.
- American options by a Cox-Ross-Rubinstein tree.
- Asian and barrier options by path simulation, with bump-and-reprice Greeks.
- A versioned snapshot of Binance BTC and ETH options, and figures that rebuild
  from it.
- 81 tests, coverage above 98 %, ruff and mypy clean.
