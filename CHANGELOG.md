# Changelog

## 1.0.0

First stable release.

- European options: Black-Scholes with a continuous dividend yield, first and
  second order Greeks, vectorised prices, deltas and vegas.
- Options on forwards: Black-76 prices, forward Greeks and implied volatility.
- American options: Cox-Ross-Rubinstein tree with dividends.
- Path-dependent options: Asian and barrier prices by Monte Carlo, antithetic
  sampling and Brownian bridge continuous monitoring.
- Path-dependent Greeks: delta, gamma and vega by finite differences with common
  paths and by likelihood ratio, compared and documented.
- Volatility: implied volatility, SVI slices with soft and hard calendar
  constraints, SSVI surfaces, butterfly and calendar diagnostics, bootstrap
  intervals and out-of-sample validation.
- Real data: versioned Binance BTC and ETH snapshots, spread-weighted
  calibration.
- Tooling: CLI with JSON output, 141 tests, 93 % branch coverage, ruff, mypy,
  pip-audit, a packaging job and 29 frozen regression values.

## 0.8.0

- `--continuous` propagated to barrier Greeks.
- Numerical regression suite with 17 frozen values.
- `docs/real_data.md` for the snapshot provenance.
- `scripts/check.py` to run lint, types and tests locally.
- 134 tests.

## 0.7.0

- Brownian bridge approximation for continuous barrier monitoring.
- `real` command to calibrate a versioned snapshot from the CLI.
- PyPI metadata with keywords, classifiers and project URLs.
- 127 tests.

## 0.6.0

- SSVI and bootstrap intervals exposed in the CLI, with JSON output.
- Optional antithetic sampling for Asian and barrier options.
- Dependency audit with pip-audit in CI.
- `docs/cli.md` for every command and flag.
- 124 tests.

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
