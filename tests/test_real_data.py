from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

from options_pricer.real_data import Quote, build_slice, load_chain
from options_pricer.surface import calibrate_from_vols

SNAPSHOT = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "binance_btc_options_2026-11-22.csv"
)


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
