from __future__ import annotations

import math

import pytest

from options_pricer.black_scholes import call_price, greeks, price, put_price

SPOT = 100.0
STRIKE = 100.0
RATE = 0.05
VOL = 0.20
EXPIRY = 1.0


def test_reference_call_price() -> None:
    assert call_price(SPOT, STRIKE, RATE, VOL, EXPIRY) == pytest.approx(10.4506, abs=1e-3)


def test_reference_put_price() -> None:
    assert put_price(SPOT, STRIKE, RATE, VOL, EXPIRY) == pytest.approx(5.5735, abs=1e-3)


def test_put_call_parity() -> None:
    call = call_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    put = put_price(SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert call - put == pytest.approx(SPOT - STRIKE * math.exp(-RATE * EXPIRY), abs=1e-10)


def test_call_greeks() -> None:
    result = greeks("call", SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.delta == pytest.approx(0.6368, abs=1e-3)
    assert result.gamma > 0.0
    assert result.vega == pytest.approx(37.52, abs=0.01)
    assert result.theta < 0.0
    assert result.rho > 0.0


def test_put_greeks() -> None:
    result = greeks("put", SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.delta == pytest.approx(-0.3632, abs=1e-3)
    assert result.gamma > 0.0
    assert result.theta < 0.0
    assert result.rho < 0.0


def test_deep_in_the_money_call_delta_tends_to_one() -> None:
    result = greeks("call", 500.0, 100.0, RATE, VOL, EXPIRY)
    assert result.delta > 0.99


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        price("call", 0.0, STRIKE, RATE, VOL, EXPIRY)
    with pytest.raises(ValueError):
        price("call", SPOT, 0.0, RATE, VOL, EXPIRY)
    with pytest.raises(ValueError):
        price("call", SPOT, STRIKE, RATE, 0.0, EXPIRY)
    with pytest.raises(ValueError):
        price("call", SPOT, STRIKE, RATE, VOL, 0.0)
    with pytest.raises(ValueError):
        price("digital", SPOT, STRIKE, RATE, VOL, EXPIRY)


def test_second_order_greeks_match_finite_differences() -> None:
    step = 1e-4
    base = greeks("call", SPOT, STRIKE, RATE, VOL, EXPIRY)

    vega_spot_up = greeks("call", SPOT + step, STRIKE, RATE, VOL, EXPIRY).vega
    vega_spot_down = greeks("call", SPOT - step, STRIKE, RATE, VOL, EXPIRY).vega
    assert base.vanna == pytest.approx(
        (vega_spot_up - vega_spot_down) / (2.0 * step), rel=1e-4
    )

    vega_vol_up = greeks("call", SPOT, STRIKE, RATE, VOL + step, EXPIRY).vega
    vega_vol_down = greeks("call", SPOT, STRIKE, RATE, VOL - step, EXPIRY).vega
    assert base.volga == pytest.approx(
        (vega_vol_up - vega_vol_down) / (2.0 * step), rel=1e-4
    )

    delta_expiry_up = greeks("call", SPOT, STRIKE, RATE, VOL, EXPIRY + step).delta
    delta_expiry_down = greeks("call", SPOT, STRIKE, RATE, VOL, EXPIRY - step).delta
    assert base.charm == pytest.approx(
        -(delta_expiry_up - delta_expiry_down) / (2.0 * step), rel=1e-3
    )


def test_second_order_greeks_are_shared_by_calls_and_puts() -> None:
    call = greeks("call", SPOT, STRIKE, RATE, VOL, EXPIRY)
    put = greeks("put", SPOT, STRIKE, RATE, VOL, EXPIRY)

    assert call.vanna == pytest.approx(put.vanna, rel=1e-12)
    assert call.volga == pytest.approx(put.volga, rel=1e-12)
    assert call.charm == pytest.approx(put.charm, rel=1e-12)


def test_second_order_greek_signs_at_the_money() -> None:
    result = greeks("call", SPOT, STRIKE, RATE, VOL, EXPIRY)
    assert result.vanna < 0.0
    assert result.volga > 0.0
    assert result.charm < 0.0
