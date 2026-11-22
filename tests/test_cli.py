from __future__ import annotations

import pytest

from options_pricer.__main__ import main


def test_price_command(capsys) -> None:
    code = main(
        [
            "price",
            "--spot",
            "100",
            "--strike",
            "100",
            "--rate",
            "0.05",
            "--vol",
            "0.2",
            "--expiry",
            "1",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "10.450584" in out
    assert "vanna" in out and "volga" in out and "charm" in out


def test_mc_command(capsys) -> None:
    code = main(
        [
            "mc",
            "--spot",
            "100",
            "--strike",
            "100",
            "--rate",
            "0.05",
            "--vol",
            "0.2",
            "--expiry",
            "1",
            "--paths",
            "10000",
            "--seed",
            "3",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "95% ci" in out
    assert "paths  10000" in out


def test_iv_command(capsys) -> None:
    code = main(
        [
            "iv",
            "--spot",
            "100",
            "--strike",
            "100",
            "--rate",
            "0.05",
            "--expiry",
            "1",
            "--price",
            "10.450584",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "implied vol  0.2" in out


def test_american_command(capsys) -> None:
    code = main(
        [
            "american",
            "--spot",
            "100",
            "--strike",
            "100",
            "--rate",
            "0.05",
            "--vol",
            "0.2",
            "--expiry",
            "1",
            "--type",
            "put",
            "--steps",
            "200",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "premium" in out
    assert "steps     200" in out


def test_asian_command(capsys) -> None:
    code = main(
        [
            "asian",
            "--spot",
            "100",
            "--strike",
            "100",
            "--rate",
            "0.05",
            "--vol",
            "0.2",
            "--expiry",
            "1",
            "--paths",
            "5000",
            "--steps",
            "20",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "stderr" in out


def test_barrier_command(capsys) -> None:
    code = main(
        [
            "barrier",
            "--spot",
            "100",
            "--strike",
            "100",
            "--rate",
            "0.05",
            "--vol",
            "0.2",
            "--expiry",
            "1",
            "--barrier",
            "120",
            "--kind",
            "up-and-out",
            "--paths",
            "5000",
            "--steps",
            "20",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "up-and-out at 120.0" in out


def test_barrier_greeks_command(capsys) -> None:
    code = main(
        [
            "barrier",
            "--spot",
            "100",
            "--strike",
            "100",
            "--rate",
            "0.05",
            "--vol",
            "0.2",
            "--expiry",
            "1",
            "--barrier",
            "150",
            "--kind",
            "up-and-out",
            "--paths",
            "5000",
            "--steps",
            "20",
            "--greeks",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "delta" in out and "vega" in out and "theta" in out


def test_surface_command(capsys) -> None:
    code = main(["surface"])
    out = capsys.readouterr().out
    assert code == 0
    assert "rmse" in out


def test_surface_all_command(capsys) -> None:
    code = main(["surface", "--all"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.count("\n") >= 5
    assert "expiry" in out


def test_missing_subcommand_exits() -> None:
    with pytest.raises(SystemExit):
        main([])
