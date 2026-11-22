"""Download a snapshot of the Binance BTC options chain.

The output CSV is versioned so the repository works without network access.
Prices are in USDT and the underlying is the BTCUSDT index.

Usage:
    python scripts/fetch_binance.py --out data/binance_btc_options_YYYY-MM-DD.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BASE = "https://eapi.binance.com/eapi/v1"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--underlying", default="BTCUSDT")
    parser.add_argument("--expiries", type=int, default=3)
    parser.add_argument("--min-days", type=float, default=7.0)
    parser.add_argument("--max-days", type=float, default=200.0)
    args = parser.parse_args()

    info = get_json(f"{BASE}/exchangeInfo")
    tickers = {item["symbol"]: item for item in get_json(f"{BASE}/ticker")}
    index_price = float(get_json(f"{BASE}/index?underlying={args.underlying}")["indexPrice"])

    now = datetime.now(UTC)
    captured_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    instruments: list[dict[str, Any]] = []
    for item in info["optionSymbols"]:
        if item.get("status") != "TRADING":
            continue
        if item.get("underlying") != args.underlying:
            continue

        expiry = datetime.fromtimestamp(item["expiryDate"] / 1000.0, tz=UTC)
        days = (expiry - now).total_seconds() / 86400.0
        if not (args.min_days <= days <= args.max_days):
            continue

        ticker = tickers.get(item["symbol"])
        if ticker is None:
            continue

        bid = float(ticker["bidPrice"])
        ask = float(ticker["askPrice"])
        if bid <= 0.0 or ask <= 0.0 or ask < bid:
            continue

        mid = 0.5 * (bid + ask)
        if mid <= 1.0:
            continue
        if (ask - bid) / mid > 0.5:
            continue

        instruments.append(
            {
                "expiry": expiry.strftime("%Y-%m-%d"),
                "days": days,
                "strike": float(item["strikePrice"]),
                "side": "C" if item["side"] == "CALL" else "P",
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "index": index_price,
                "captured_at": captured_at,
                "volume_usdt": float(ticker.get("amount", 0.0) or 0.0),
            }
        )

    by_expiry: dict[str, list[dict[str, Any]]] = {}
    for row in instruments:
        by_expiry.setdefault(row["expiry"], []).append(row)

    ranked = sorted(
        by_expiry.items(),
        key=lambda item: sum(row["volume_usdt"] for row in item[1]),
        reverse=True,
    )[: args.expiries]

    selected = [row for _, rows in ranked for row in rows]
    if not selected:
        raise SystemExit("no liquid instruments found")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "expiry",
        "days",
        "strike",
        "side",
        "bid",
        "ask",
        "mid",
        "index",
        "captured_at",
    ]
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(selected)

    print(f"index {index_price:.2f} USDT at {captured_at}")
    for expiry_key, rows in ranked:
        sides = {row["side"] for row in rows}
        print(f"{expiry_key}: {len(rows)} quotes, sides {sorted(sides)}")
    print(f"wrote {len(selected)} rows to {args.out}")


if __name__ == "__main__":
    main()
