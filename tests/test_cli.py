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


def test_forward_command(capsys) -> None:
    code = main(
        [
            "forward",
            "--forward",
            "105.12710963760242",
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
    assert "10.450" in out


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


def test_price_json(capsys) -> None:
    import json

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
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["price"] == pytest.approx(10.450584, abs=1e-6)
    assert payload["delta"] == pytest.approx(0.636831, abs=1e-6)


def test_barrier_json_includes_kind(capsys) -> None:
    import json

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
            "--paths",
            "5000",
            "--steps",
            "20",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["kind"] == "up-and-out"
    assert payload["barrier"] == 120.0
    assert "price" in payload


def test_surface_json_is_a_list_when_all(capsys) -> None:
    import json

    code = main(["surface", "--all", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert isinstance(payload, list)
    assert len(payload) == 4
    assert "rmse" in payload[0]


def test_ssvi_command(capsys) -> None:
    code = main(["ssvi"])
    out = capsys.readouterr().out
    assert code == 0
    assert "rho" in out and "eta" in out and "gamma" in out


def test_bootstrap_command(capsys) -> None:
    code = main(
        [
            "bootstrap",
            "--spot",
            "100",
            "--strike",
            "100",
            "--rate",
            "0.03",
            "--vol",
            "0.2",
            "--expiry",
            "1",
            "--samples",
            "20",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "samples" in out
    assert "rmse" in out


def test_real_command(capsys) -> None:
    from pathlib import Path

    snapshot = (
        Path(__file__).resolve().parent.parent / "data" / "binance_btc_options_2026-11-22.csv"
    )
    code = main(["real", "--input", str(snapshot)])
    out = capsys.readouterr().out
    assert code == 0
    assert "2026-12-25" in out
    assert "60875" in out
