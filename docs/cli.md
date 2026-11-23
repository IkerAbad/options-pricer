# Command line

Every command is available after `pip install options-pricer` and accepts
`--json` for machine-readable output, except where noted.

## price

```
options-pricer price --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1
```

Black-Scholes price and the eight Greeks. `--type put` switches to a put.

## mc

```
options-pricer mc --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1 --paths 1000000
```

Monte Carlo price with antithetic variates, standard error and a 95 % interval.
`--seed` fixes the draws.

## iv

```
options-pricer iv --spot 100 --strike 100 --rate 0.05 --expiry 1 --price 10.450584
```

Implied volatility from a quoted price. Prices below intrinsic value are
rejected.

## forward

```
options-pricer forward --forward 105.1271 --strike 100 --rate 0.05 --vol 0.2 --expiry 1
```

Black-76 price and forward Greeks for an option on a forward or future.

## american

```
options-pricer american --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1 --type put
```

Cox-Ross-Rubinstein tree. `--steps` controls the tree, `--dividend` sets a
continuous yield. American and European prices come from the same tree.

## asian

```
options-pricer asian --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1
```

Arithmetic-average Asian option. `--steps`, `--paths` and `--seed` control the
simulation.

## barrier

```
options-pricer barrier --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1 --barrier 120
```

Barrier option with discrete monitoring. `--kind` takes `up-and-out`,
`up-and-in`, `down-and-out` or `down-and-in`. Add `--greeks` for delta, vega and
theta by bump and reprice.

## surface

```
options-pricer surface
options-pricer surface --all
```

Calibrates a synthetic SVI smile, or four expiries with `--all`. `--noise` sets
the relative price noise.

## ssvi

```
options-pricer ssvi
```

Calibrates a synthetic SSVI surface with three global parameters and reports
whether it is free of calendar arbitrage.

## bootstrap

```
options-pricer bootstrap --spot 100 --strike 100 --rate 0.03 --vol 0.2 --expiry 1 --samples 100
```

Bootstrap intervals for the five SVI parameters on a synthetic smile. `--noise`
controls the quote noise and `--seed` the resampling.
