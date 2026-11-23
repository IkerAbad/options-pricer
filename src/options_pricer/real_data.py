"""Read a versioned options snapshot and turn it into SVI-ready slices."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .black_scholes import OptionType
from .implied_vol import implied_volatility


@dataclass(frozen=True)
class Quote:
    expiry: str
    days: float
    strike: float
    side: str
    mid: float
    index: float
    bid: float = 0.0
    ask: float = 0.0


@dataclass(frozen=True)
class Slice:
    expiry: str
    forward: float
    years: float
    log_moneyness: list[float]
    vols: list[float]
    strikes: list[float]
    weights: list[float]


def load_chain(path: Path) -> list[Quote]:
    quotes: list[Quote] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            quotes.append(
                Quote(
                    expiry=row["expiry"],
                    days=float(row["days"]),
                    strike=float(row["strike"]),
                    side=row["side"],
                    mid=float(row["mid"]),
                    index=float(row["index"]),
                    bid=float(row.get("bid", 0.0)),
                    ask=float(row.get("ask", 0.0)),
                )
            )
    return quotes


def forward_from_parity(quotes: list[Quote]) -> float:
    """Implied forward from the call-put pair closest to the index.

    With a zero rate the parity is C - P = F - K, so F = K + C - P. Using zero
    is an approximation for crypto, where the funding basis is small but not
    zero. The figure and the calibration use the same forward, so the slice stays
    internally consistent.
    """
    calls = {quote.strike: quote.mid for quote in quotes if quote.side == "C"}
    puts = {quote.strike: quote.mid for quote in quotes if quote.side == "P"}
    common = sorted(set(calls) & set(puts))
    if not common:
        return quotes[0].index

    strike = min(common, key=lambda value: abs(value - quotes[0].index))
    return strike + calls[strike] - puts[strike]


def build_slice(
    quotes: list[Quote],
    min_moneyness: float = 0.5,
    max_moneyness: float = 2.0,
) -> Slice:
    forward = forward_from_parity(quotes)
    years = quotes[0].days / 365.0

    log_moneyness: list[float] = []
    vols: list[float] = []
    strikes: list[float] = []
    weights: list[float] = []

    for quote in quotes:
        if not (min_moneyness * forward <= quote.strike <= max_moneyness * forward):
            continue

        kind: OptionType = "call" if quote.side == "C" else "put"
        try:
            vol = implied_volatility(quote.mid, forward, quote.strike, 0.0, years, kind)
        except ValueError:
            continue
        if not (0.02 < vol < 3.0):
            continue

        spread = (
            (quote.ask - quote.bid) / quote.mid
            if quote.ask > quote.bid and quote.mid > 0.0
            else 0.01
        )

        log_moneyness.append(math.log(quote.strike / forward))
        vols.append(vol)
        strikes.append(quote.strike)
        weights.append(1.0 / max(spread, 1e-4))

    mean_weight = sum(weights) / len(weights) if weights else 1.0
    weights = [weight / mean_weight for weight in weights]

    return Slice(
        expiry=quotes[0].expiry,
        forward=forward,
        years=years,
        log_moneyness=log_moneyness,
        vols=vols,
        strikes=strikes,
        weights=weights,
    )


def load_history_day(path: Path) -> tuple[str, list[Quote]]:
    """Load one reconstructed day from `scripts/fetch_history.py`.

    Prices are daily closes, so bid and ask are set to the close and the spread
    weights fall back to the default.
    """
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    day = rows[0]["date"]
    day_date = datetime.strptime(day, "%Y-%m-%d")
    quotes: list[Quote] = []

    for row in rows:
        expiry = row["expiry"]
        days = (datetime.strptime(expiry, "%Y-%m-%d") - day_date).days
        mid = float(row["close"])
        if days <= 0 or mid <= 0.0:
            continue
        quotes.append(
            Quote(
                expiry=expiry,
                days=float(days),
                strike=float(row["strike"]),
                side=row["side"],
                mid=mid,
                index=float(row["index"]),
                bid=mid,
                ask=mid,
            )
        )

    return day, quotes
