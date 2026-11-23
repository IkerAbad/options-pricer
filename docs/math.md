# Mathematics

The formulas behind the code, in plain text. Every expression here is implemented
in the package and checked by a test.

## Black-Scholes with a continuous dividend yield

With spot S, strike K, rate r, dividend yield q, volatility σ and expiry T:

```
d1 = (ln(S/K) + (r - q + σ²/2) T) / (σ √T)
d2 = d1 - σ √T
C  = S e^(-qT) N(d1) - K e^(-rT) N(d2)
P  = K e^(-rT) N(-d2) - S e^(-qT) N(-d1)
```

`N` is the standard normal CDF. The code computes it with `0.5 * erfc(-x/√2)`,
which is faster than a library call and accurate in the tails.

## Put-call parity

With a dividend yield:

```
C - P = S e^(-qT) - K e^(-rT)
```

The test asserts this to 1e-10. In Monte Carlo the same identity holds path by
path when both prices use the same random draws, which is why the test compares
against the sample mean terminal price and not against the theoretical forward.

## Greeks

```
delta_call = e^(-qT) N(d1)                 delta_put = -e^(-qT) N(-d1)
gamma      = e^(-qT) φ(d1) / (S σ √T)
vega       = S e^(-qT) φ(d1) √T
theta_call = -S e^(-qT) φ(d1) σ / (2√T) + q S e^(-qT) N(d1) - r K e^(-rT) N(d2)
theta_put  = -S e^(-qT) φ(d1) σ / (2√T) - q S e^(-qT) N(-d1) + r K e^(-rT) N(-d2)
rho_call   = K T e^(-rT) N(d2)             rho_put = -K T e^(-rT) N(-d2)
vanna      = -e^(-qT) φ(d1) d2 / σ
volga      = S e^(-qT) φ(d1) √T d1 d2 / σ
charm      = -∂delta/∂T
```

`φ` is the standard normal density. Vega is per unit of volatility, not per
percentage point. Theta is per year. Charm is checked against central finite
differences of delta in T, with and without dividends.

## Black-76

For an option on a forward F, the same formulas apply with S e^(-qT) replaced by
e^(-rT) F:

```
C = e^(-rT) (F N(d1) - K N(d2))
P = e^(-rT) (K N(-d2) - F N(-d1))
d1 = (ln(F/K) + σ² T/2) / (σ √T)
```

Setting F = S e^((r-q)T) recovers Black-Scholes exactly, which is the consistency
test.

## Monte Carlo

The terminal price is sampled from its exact distribution:

```
S_T = S exp((r - q - σ²/2) T + σ √T Z),   Z ~ N(0, 1)
```

No Euler discretisation, so there is no bias in the terminal law. Antithetic
sampling pairs each Z with -Z. The standard error of the discounted payoff is
s/√n, and the 95 % interval is the estimate ± 1.96 standard errors.

## Binomial tree

Cox-Ross-Rubinstein with N steps and dt = T/N:

```
u = e^(σ √dt)      d = 1/u      p = (e^((r-q)dt) - d) / (u - d)
V = max(intrinsic, e^(-r dt) (p V_up + (1-p) V_down))
```

For a European option the maximum with the intrinsic value is removed. American
and European prices are computed on the same tree so the early exercise premium
carries no discretisation noise between the two.

## SVI

The raw SVI parametrisation of total implied variance w = σ² T:

```
w(k) = a + b (ρ (k - m) + √((k - m)² + σ²))
k    = ln(K / F)
```

The five parameters are fitted by bounded least squares. `m` shifts the smile,
`ρ` controls its skew, `σ` its curvature, `b` its slope and `a` the overall level.

## No arbitrage

Butterfly, from Gatheral:

```
g(k) = (1 - k w'/(2w))² - (w'²/4) (1/w + 1/4) + w''/2
```

`g(k) >= 0` everywhere means the implied density is non-negative. The code
evaluates it on a grid and reports the share of points below zero.

Calendar: total variance cannot decrease with maturity,

```
w(k, T2) >= w(k, T1)   for T2 > T1
```

The default calibration penalises violations softly. `hard_calendar=True` imposes
the inequality with SLSQP, one constraint per grid point, at the cost of a slower
fit and a higher RMSE.
