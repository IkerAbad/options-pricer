from __future__ import annotations

import pytest

from options_pricer.ssvi import (
    SsviParams,
    atm_total_variance,
    calibrate_ssvi,
    implied_vol,
    is_arbitrage_free,
)

TRUE = SsviParams(rho=-0.4, eta=0.8, gamma=0.4)


def synthetic_slices():
    expiries = [0.25, 0.5, 1.0]
    ks = [i * 0.1 - 0.4 for i in range(9)]
    slices = []
    thetas = []
    for expiry in expiries:
        theta = 0.05 * expiry
        thetas.append(theta)
        slices.append([implied_vol(k, expiry, theta, TRUE) for k in ks])
    return expiries, [ks for _ in expiries], slices, thetas


def test_atm_total_variance_uses_the_closest_strike() -> None:
    assert atm_total_variance([-0.2, -0.05, 0.1], [0.3, 0.2, 0.25], 2.0) == pytest.approx(
        0.04 * 2.0
    )


def test_ssvi_implied_vol_is_positive() -> None:
    for k in (-0.5, -0.2, 0.0, 0.2, 0.5):
        assert implied_vol(k, 1.0, 0.05, TRUE) > 0.0


def test_calibration_recovers_a_synthetic_surface() -> None:
    expiries, ks, vols, _ = synthetic_slices()
    params, rmse, thetas = calibrate_ssvi(expiries, ks, vols)

    assert rmse < 0.005
    assert params.rho == pytest.approx(TRUE.rho, abs=0.15)
    assert len(thetas) == len(expiries)


def test_arbitrage_free_check() -> None:
    assert is_arbitrage_free(SsviParams(rho=-0.4, eta=0.8, gamma=0.4))
    assert not is_arbitrage_free(SsviParams(rho=-0.9, eta=3.5, gamma=0.4))


def test_mismatched_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        calibrate_ssvi([1.0], [[0.0], [0.1]], [[0.2]])
    with pytest.raises(ValueError):
        calibrate_ssvi([], [], [])
    with pytest.raises(ValueError):
        atm_total_variance([], [], 1.0)


def test_round_trip_through_a_dictionary() -> None:
    assert SsviParams.from_dict(TRUE.to_dict()) == TRUE
