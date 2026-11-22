"""Cross-checks against QuantLib.

These tests are skipped when QuantLib is not installed. It is not a runtime
dependency, only an external reference used during development.
"""

from __future__ import annotations

import pytest

ql = pytest.importorskip("QuantLib")

from options_pricer.american import binomial  # noqa: E402
from options_pricer.black_scholes import call_price, put_price  # noqa: E402

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def build_process():
    day_count = ql.Actual365Fixed()
    calendar = ql.NullCalendar()
    today = ql.Date(22, 11, 2026)
    ql.Settings.instance().evaluationDate = today

    spot = ql.QuoteHandle(ql.SimpleQuote(SPOT))
    rate = ql.YieldTermStructureHandle(ql.FlatForward(today, RATE, day_count))
    dividend = ql.YieldTermStructureHandle(ql.FlatForward(today, 0.0, day_count))
    vol = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, calendar, VOL, day_count))
    return ql.BlackScholesMertonProcess(spot, dividend, rate, vol)


def maturity() -> ql.Date:
    return ql.Date(22, 11, 2027)


def test_european_call_matches_quantlib() -> None:
    option = ql.VanillaOption(
        ql.PlainVanillaPayoff(ql.Option.Call, STRIKE),
        ql.EuropeanExercise(maturity()),
    )
    option.setPricingEngine(ql.AnalyticEuropeanEngine(build_process()))

    assert option.NPV() == pytest.approx(call_price(SPOT, STRIKE, RATE, VOL, EXPIRY), abs=1e-6)


def test_european_put_matches_quantlib() -> None:
    option = ql.VanillaOption(
        ql.PlainVanillaPayoff(ql.Option.Put, STRIKE),
        ql.EuropeanExercise(maturity()),
    )
    option.setPricingEngine(ql.AnalyticEuropeanEngine(build_process()))

    assert option.NPV() == pytest.approx(put_price(SPOT, STRIKE, RATE, VOL, EXPIRY), abs=1e-6)


def test_american_put_matches_quantlib_binomial() -> None:
    option = ql.VanillaOption(
        ql.PlainVanillaPayoff(ql.Option.Put, STRIKE),
        ql.AmericanExercise(ql.Settings.instance().evaluationDate, maturity()),
    )
    option.setPricingEngine(ql.BinomialVanillaEngine(build_process(), "crr", 1_000))

    assert option.NPV() == pytest.approx(
        binomial("put", SPOT, STRIKE, RATE, VOL, EXPIRY, steps=1_000).american,
        abs=0.02,
    )


def test_american_call_with_dividends_matches_quantlib() -> None:
    dividend = 0.08
    day_count = ql.Actual365Fixed()
    today = ql.Settings.instance().evaluationDate
    process = ql.BlackScholesMertonProcess(
        ql.QuoteHandle(ql.SimpleQuote(SPOT)),
        ql.YieldTermStructureHandle(ql.FlatForward(today, dividend, day_count)),
        ql.YieldTermStructureHandle(ql.FlatForward(today, RATE, day_count)),
        ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(today, ql.NullCalendar(), VOL, day_count)
        ),
    )
    option = ql.VanillaOption(
        ql.PlainVanillaPayoff(ql.Option.Call, STRIKE),
        ql.AmericanExercise(today, maturity()),
    )
    option.setPricingEngine(ql.BinomialVanillaEngine(process, "crr", 1_000))

    assert option.NPV() == pytest.approx(
        binomial(
            "call",
            SPOT,
            STRIKE,
            RATE,
            VOL,
            EXPIRY,
            steps=1_000,
            dividend_yield=dividend,
        ).american,
        abs=0.03,
    )
