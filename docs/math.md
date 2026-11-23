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

## Path-dependent Greeks

Two independent estimators for delta, gamma and vega of an Asian or barrier
option.

### Finite differences with common random numbers

Reprice at `S(1+h)`, `S(1-h)`, `σ+h` and `σ-h` with the same seed. The shocks are
identical, so the Monte Carlo noise cancels in the difference:

```
delta = (P(S(1+h)) - P(S(1-h))) / (2 S h)
gamma = (P(S(1+h)) - 2 P(S) + P(S(1-h))) / (S h)^2
vega  = (P(σ+h) - P(σ-h)) / (2 h)
```

The variance is low, but the barrier payoff is discontinuous. A bump moves paths
across the barrier, so the difference includes a jump that does not shrink with
`h`. The estimator is biased for any finite bump.

### Likelihood ratio

Hold the payoff fixed and differentiate the density instead. With log-returns
`Δx_i ~ N(μ dt, σ² dt)` and `d_i = Δx_i - μ dt`, the scores are

```
score_S = (Δx_1 - μ dt) / (S σ² dt)
score_σ = Σ_i [ -(1 + d_i)/σ + d_i² / (σ³ dt) ]

delta = E[P score_S]
gamma = E[P (score_S² + ∂score_S/∂S)]
vega  = E[P score_σ]
```

with

```
∂score_S/∂S = -(1 + Δx_1 - μ dt) / (S² σ² dt)
```

The spot enters only the first transition, because the log-returns are
independent of the initial level. The volatility enters every transition, which
is why its score is a sum and its variance is larger. Using the terminal score
for the spot is wrong for a path-dependent payoff: it is only valid when the
payoff is a function of the terminal price alone.

### Why the likelihood ratio is more stable near the barrier

The barrier payoff is discontinuous. Finite differences differentiate the payoff,
and a tiny bump can move a path from below the barrier to above it. That jump
enters the difference with a weight of `1/(2h)`, so the estimator carries a bias
that does not vanish as `h → 0`. The likelihood ratio holds the payoff fixed and
moves the density, so the discontinuity never enters. The cost is variance, not
bias.

Measured on this repository with 100,000 paths for finite differences and
1,000,000 for the likelihood ratio, errors relative to a likelihood-ratio
reference with 2,000,000 paths:

| Option | Method | Delta | Gamma | Vega | Time |
| --- | --- | --- | --- | --- | --- |
| Asian call | FD, common paths | 0.15 % | 2.14 % | 0.26 % | 1.33 s |
| Asian call | FD, independent paths | 0.32 % | 123.55 % | 0.93 % | 1.29 s |
| Asian call | Likelihood ratio | 0.72 % | 0.44 % | 2.82 % | 4.60 s |
| Up-and-out, barrier 120 | FD, common paths | 50.33 % | 103.79 % | 5.77 % | 1.27 s |
| Up-and-out, barrier 120 | FD, independent paths | 43.01 % | 243.05 % | 7.84 % | 1.29 s |
| Up-and-out, barrier 120 | Likelihood ratio | 2.20 % | 13.13 % | 1.21 % | 4.27 s |

For the Asian, finite differences are cheaper and accurate. For the barrier, the
discontinuity breaks them: the delta error is tens of percent, while the
likelihood ratio stays in single digits. The price is time and variance, and the
barrier gamma remains the hardest quantity either way.
