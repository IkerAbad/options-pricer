# Multi-day calibration

Five daily BTC option chains, reconstructed from Binance option klines, to check
whether the SVI calibration holds over time and not only on one snapshot.

## Provenance

- Source: Binance Options EAPI `klines`, underlying `BTCUSDT`.
- Days: 2026-11-19 to 2026-11-23.
- Files: `data/history/binance_btc_options_YYYY-MM-DD.csv`.
- Hashes and capture time: `data/history/manifest.json`.
- Prices are daily closes, that is, the last trade of each instrument. They are
  not bid or ask, and there is no spread.
- The index is the Binance spot BTCUSDT close of the same day.
- 115 to 162 quotes per day across three expiries. The 2026-12-25 expiry has 41
  to 57 quotes.

The reconstruction script is `scripts/fetch_history.py`. It uses the instruments
that had liquidity in the 2026-11-22 snapshot, so the history is conditioned on
today's liquid strikes.

## Results

Parameters for the 2026-12-25 expiry, calibrated day by day. RMSE in vol points.

| Date | Days | Forward | Quotes | a | b | rho | m | sigma | RMSE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-19 | 36.0 | 62,460.00 | 41 | 0.0027 | 0.0870 | -0.190 | 0.043 | 0.162 | 3.55 |
| 2026-11-20 | 35.0 | 59,070.00 | 48 | 0.0109 | 0.0879 | -0.275 | 0.072 | 0.110 | 6.47 |
| 2026-11-21 | 34.0 | 60,520.00 | 57 | 0.0218 | 0.1492 | +0.224 | -0.008 | 0.017 | 30.23 |
| 2026-11-22 | 33.0 | 61,405.00 | 42 | 0.0130 | 0.1004 | -0.369 | -0.028 | 0.105 | 12.24 |
| 2026-11-23 | 32.0 | 63,240.00 | 48 | -0.0251 | 0.1258 | -0.063 | 0.078 | 0.325 | 4.33 |

The full table for the three expiries is in `docs/history_calibration.csv`.

## Stability

The calibration is not stable on this series.

- `b` is the only parameter that stays in a reasonable band: 0.087 to 0.149,
  a range of 0.062.
- `a` changes sign: from +0.0218 to -0.0251.
- `rho` changes sign: from -0.369 to +0.224.
- `m` changes sign as well.
- `sigma` varies by a factor of 19: from 0.017 to 0.325.
- The RMSE ranges from 3.55 to 30.23 vol points.

2026-11-21 is the outlier. `sigma` collapses to 0.017, which makes the smile
explode in the wings, and the RMSE reaches 30 vol points. The fit is bad and the
figure shows it: that day's curve is far above the rest.

Why this happens, without dressing it up:

- Daily closes are last trades, so a quote can be hours old and far from the
  mid. The single snapshot with bid and ask is cleaner by construction.
- Each day has 41 to 57 quotes for that expiry, and five SVI parameters are not
  identified by that few points.
- The instrument set is conditioned on what was liquid on 2026-11-22. Strikes
  that were liquid on other days are missing.

This does not invalidate the snapshot calibration. It shows the limit of
calibrating a five-parameter smile on a thin, noisy daily chain, which is a
different and honest result.

## Reproduce

```
python scripts/fetch_history.py
python scripts/calibrate_history.py
```

The second command writes `docs/history_calibration.csv` and
`docs/history_calibration.png`. The 2026-11-22 snapshot is frozen in
`tests/test_regression.py`.
