# Tutorial

A complete pass over the package, from a single price to a calibrated surface.
Every command works after `pip install options-pricer`.

## 1. One European price

```
options-pricer price --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1
```

The call is worth 10.450584, with delta 0.636831 and vega 37.524035. The output
also includes gamma, theta, rho, vanna, volga and charm.

From Python:

```python
from options_pricer import call_price, greeks

value = call_price(100, 100, 0.05, 0.20, 1.0)
delta = greeks("call", 100, 100, 0.05, 0.20, 1.0).delta
```

## 2. Monte Carlo

```
options-pricer mc --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1 --paths 1000000
```

The interval contains the analytic price. The standard error falls with the
square root of the number of paths, and antithetic sampling is on by default.

## 3. Implied volatility

```
options-pricer iv --spot 100 --strike 100 --rate 0.05 --expiry 1 --price 10.450584
```

The answer is 0.2, the volatility that generated the quote. Prices below the
intrinsic value are rejected instead of returning a meaningless number.

## 4. A synthetic smile

```
options-pricer surface
```

The command builds a smile from known SVI parameters, adds 0.1 % price noise and
fits it back. The RMSE is reported in volatility points.

## 5. A real snapshot

The repository ships a Binance BTC snapshot:

```
python scripts/real_smile.py
```

The table shows the forward, the number of quotes and the RMSE for each expiry.
The forward comes from put-call parity, not from an assumed rate.

## 6. American and path-dependent options

```
options-pricer american --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1 --type put
options-pricer asian --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1
options-pricer barrier --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1 --barrier 120
```

The American put carries an early exercise premium. The Asian is cheaper than the
European because averaging removes variance. The barrier is monitored at the
simulation steps, not continuously.

## 7. Machine-readable output

Add `--json` to any command:

```
options-pricer price --spot 100 --strike 100 --rate 0.05 --vol 0.2 --expiry 1 --json
```

The same flag works on `mc`, `iv`, `forward`, `american`, `asian`, `barrier` and
`surface`. SVI parameters serialise with `to_dict` and `from_dict`.

## 8. Where to look next

- `README.md` for the results and the design decisions.
- `https://ikerabad.github.io/options-pricer/` for the API reference.
- `tests/` for the numerical checks, including the QuantLib cross-checks.
