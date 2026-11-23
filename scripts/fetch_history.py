"""Reconstruct five daily BTC option chains from Binance option klines.

The option klines endpoint returns the daily open, high, low, close and volume
for each instrument. The chain is rebuilt with the last close of each day and
the spot close as the index.

Usage:
    python scripts/fetch_history.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

OPTIONS = "https://eapi.binance.com/eapi/v1"
SPOT = "https://api.binance.com/api/v3/klines"
ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "binance_btc_options_2026-11-22.csv"
OUTPUT = ROOT / "data" / "history"
DAYS = 5

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main() -> None:
    info = get_json(f"{OPTIONS}/exchangeInfo")
    by_key: dict[tuple[str, float, str], str] = {}
    for item in info["optionSymbols"]:
        if item.get("underlying") != "BTCUSDT":
            continue
        expiry = datetime.fromtimestamp(item["expiryDate"] / 1000.0, tz=UTC).strftime("%Y-%m-%d")
        side = "C" if item["side"] == "CALL" else "P"
        by_key[(expiry, float(item["strikePrice"]), side)] = item["symbol"]

    with SNAPSHOT.open(newline="", encoding="utf-8") as handle:
        current = list(csv.DictReader(handle))

    instruments: dict[str, tuple[str, float, str]] = {}
    for row in current:
        key = (row["expiry"], float(row["strike"]), row["side"])
        symbol = by_key.get(key)
        if symbol is not None:
            instruments[symbol] = key

    spot = get_json(f"{SPOT}?symbol=BTCUSDT&interval=1d&limit=10")
    spot_close = {
        datetime.fromtimestamp(candle[0] / 1000.0, tz=UTC).strftime("%Y-%m-%d"): float(candle[4])
        for candle in spot
    }

    rows_by_day: dict[str, list[dict[str, object]]] = {}

    for index, (symbol, (expiry, strike, side)) in enumerate(instruments.items()):
        klines = get_json(f"{OPTIONS}/klines?symbol={symbol}&interval=1d&limit=10")
        for candle in klines:
            day = datetime.fromtimestamp(candle[0] / 1000.0, tz=UTC).strftime("%Y-%m-%d")
            close = float(candle[4])
            volume = float(candle[5])
            if close <= 0.0 or volume <= 0.0:
                continue
            rows_by_day.setdefault(day, []).append(
                {
                    "date": day,
                    "symbol": symbol,
                    "expiry": expiry,
                    "strike": strike,
                    "side": side,
                    "close": close,
                    "volume": volume,
                    "index": spot_close.get(day, 0.0),
                }
            )
        if index % 50 == 0:
            time.sleep(0.05)

    days = sorted(rows_by_day)[-DAYS:]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "source": "Binance Options EAPI klines, underlying BTCUSDT",
        "captured_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Daily close and volume per instrument. Index from Binance spot BTCUSDT close.",
        "days": {},
    }

    for day in days:
        rows = rows_by_day[day]
        target = OUTPUT / f"binance_btc_options_{day}.csv"
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        manifest["days"][day] = {
            "file": target.name,
            "sha256": digest,
            "rows": len(rows),
        }
        print(f"{day}: {len(rows)} rows, sha256 {digest[:16]}")

    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(days)} days to {OUTPUT}")


if __name__ == "__main__":
    main()
