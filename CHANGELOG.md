# Changelog

## 0.5.0

- Quotes weighted by the inverse relative bid-ask spread.
- The binomial tree updates its price vector incrementally, 2.5 times faster.
- SSVI accepts the same weights as the slice calibration.
- 120 tests.

## 0.4.0

- SSVI surface calibration with three global parameters and a no-arbitrage
  check.
- Vectorised deltas and vegas.
- SSVI compared against one SVI slice per expiry on the real snapshot.
- pip cache in CI.
- 117 tests.

## 0.3.0

- Vectorised Black-Scholes prices for arrays, 33 million per second.
- Bootstrap intervals for the SVI parameters.
- Out-of-sample validation on the real snapshot.
- Benchmarks for the binomial tree and the path-dependent engines.
- `docs/tutorial.md` and `docs/math.md`.
- 108 tests.

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
