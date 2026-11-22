# Changelog

## 0.2.0

- Black-76 prices, forward Greeks and implied volatility for options on a
  forward.
- Continuous dividend yield in Black-Scholes prices and Greeks.
- JSON output in every CLI command.
- SVI parameters serialise to and from plain dictionaries.
- Benchmarks for the SVI calibration, the Monte Carlo engine and Black-Scholes.
- Black-Scholes moved from `scipy.stats.norm` to `math.erfc`, a hundred times
  faster with identical prices.
- Cross-checks against QuantLib for European and American prices.- Branch coverage, mypy on the scripts and Python 3.14 in CI.
- 101 tests, 94 % branch coverage.

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
