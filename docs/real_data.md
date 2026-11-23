# Real market data

The repository ships two versioned snapshots of the Binance options chain, one
for BTC and one for ETH. They are there so the calibration can be reproduced
without network access.

## How the snapshot was taken

- Source: Binance Options EAPI, `exchangeInfo`, `ticker` and `index`.
- Captured: 2026-11-22 at 20:22 UTC for BTC and 20:53 UTC for ETH.
- Index at capture: 60,637.68 USDT for BTC and 1,719.81 USDT for ETH.
- Filter: status `TRADING`, positive bid and ask, ask not below bid, mid above
  1 USDT, relative spread below 50 %, and expiry between 7 and 200 days.
- Selection: the three expiries with the most traded notional.
- BTC: 446 quotes. ETH: 200 quotes.

## What the files contain

`expiry, days, strike, side, bid, ask, mid, index, captured_at`

Prices are in USDT. `side` is `C` or `P`. `days` is the time to expiry at the
moment of capture, so `years = days / 365`.

## How the calibration uses them

- The forward comes from put-call parity on the pair closest to the index, with
  a zero rate: `F = K + C - P`.
- The implied volatility of each quote is computed against that forward.
- Quotes are weighted by the inverse of their relative bid-ask spread, so a
  tight quote counts more than a wide one.
- The maturity set is calibrated from short to long, each slice starting from the
  previous one, with the calendar constraint imposed by SLSQP.

## Limitations

- One snapshot per asset. There is no time series, so nothing here tests
  stability across days.
- Zero rate. The crypto basis is small but not zero, and the forward from parity
  absorbs most of it.
- Linear options only. Deribit's inverse contracts would need a different
  conversion.
- The filter removes wide quotes, which also removes some genuine but illiquid
  strikes.
