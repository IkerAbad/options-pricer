from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

from options_pricer.real_data import Quote, build_slice, forward_from_parity, load_chain
from options_pricer.surface import calibrate_from_vols

SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "binance_btc_options_2026-11-22.csv"


@pytest.fixture(scope="module")
def quotes() -> list[Quote]:
    return load_chain(SNAPSHOT)


def test_snapshot_has_three_expiries_with_both_sides(quotes: list[Quote]) -> None:
    by_expiry: dict[str, set[str]] = defaultdict(set)
    for quote in quotes:
        by_expiry[quote.expiry].add(quote.side)

    assert len(by_expiry) == 3
    for sides in by_expiry.values():
        assert sides == {"C", "P"}


def test_every_slice_calibrates_below_three_vol_points(quotes: list[Quote]) -> None:
    by_expiry: dict[str, list[Quote]] = defaultdict(list)
    for quote in quotes:
        by_expiry[quote.expiry].append(quote)

    for expiry in sorted(by_expiry, key=lambda key: by_expiry[key][0].days):
        current = build_slice(by_expiry[expiry])
        assert len(current.vols) >= 5

        params, rmse = calibrate_from_vols(
            current.years, current.log_moneyness, current.vols, ridge=1e-2
        )

        assert rmse < 0.03
        assert params.b > 0.0
        assert 0.0 < params.sigma < 0.5


def test_forward_is_above_the_index_for_this_snapshot(quotes: list[Quote]) -> None:
    current = build_slice([quote for quote in quotes if quote.expiry == "2026-12-25"])
    assert current.forward == pytest.approx(60_875.0, rel=1e-3)


def test_slice_weights_have_mean_one(quotes: list[Quote]) -> None:
    current = build_slice([quote for quote in quotes if quote.expiry == "2026-12-25"])
    assert len(current.weights) == len(current.vols)
    assert sum(current.weights) / len(current.weights) == pytest.approx(1.0)


def test_forward_falls_back_to_the_index_without_a_pair() -> None:
    quotes = [
        Quote("2026-12-25", 32.5, 100.0, "C", 5.0, 101.0),
        Quote("2026-12-25", 32.5, 110.0, "C", 3.0, 101.0),
    ]
    assert forward_from_parity(quotes) == 101.0


def test_build_slice_filters_zero_prices() -> None:
    quotes = [
        Quote("2026-12-25", 32.5, 90.0, "P", 4.0, 100.0),
        Quote("2026-12-25", 32.5, 100.0, "C", 5.0, 100.0),
        Quote("2026-12-25", 32.5, 110.0, "C", 1.0, 100.0),
        Quote("2026-12-25", 32.5, 120.0, "C", 0.0, 100.0),
    ]
    current = build_slice(quotes)
    assert 120.0 not in current.strikes
    assert len(current.vols) == len(current.strikes)
