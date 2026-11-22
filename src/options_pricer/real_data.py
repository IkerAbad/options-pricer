"""Read a versioned options snapshot and turn it into SVI-ready slices."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Slice:
    expiry: str
    forward: float
    years: float
    log_moneyness: list[float]
    vols: list[float]
    strikes: list[float]


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

        log_moneyness.append(math.log(quote.strike / forward))
        vols.append(vol)
        strikes.append(quote.strike)

    return Slice(
        expiry=quotes[0].expiry,
        forward=forward,
        years=years,
        log_moneyness=log_moneyness,
        vols=vols,
        strikes=strikes,
    )
