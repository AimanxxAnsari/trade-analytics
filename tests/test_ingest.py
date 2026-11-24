"""Journal conversion: parsing, mapping, derivations, row problems, CLI."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from trade_analytics.cli import main
from trade_analytics.ingest import (
    ConversionOptions,
    JournalConversionError,
    auto_map,
    convert_journal,
    normalise_header,
    parse_direction,
    parse_numbers,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "alien_journals"
TESTING_JOURNAL = Path(__file__).resolve().parents[1] / "data/testing_journal/testing_journal.csv"


def _raw(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


# ------------------------------------------------------------------ parsing


def test_normalise_header():
    assert normalise_header(" P&L ") == "p l"
    assert normalise_header("S / L") == "s l"
    assert normalise_header("Open_Time") == "open time"


def test_parse_numbers_handles_text_formats():
    s = pd.Series(["$1,234.50", "(320.50)", "-7", "−12.5", "abc", None])
    out = parse_numbers(s)
    assert out[:4].tolist() == [1234.5, -320.5, -7.0, -12.5]
    assert out[4:].isna().all()


def test_parse_direction_words():
    s = pd.Series(["Buy", "SELL", "long", "Short", "buy limit", "-1", "1", "flat", None])
    assert parse_direction(s).tolist()[:7] == [
        "long",
        "short",
        "long",
        "short",
        "long",
        "short",
        "long",
    ]
    assert parse_direction(s)[7:].isna().all()


def test_auto_map_prefers_explicit_and_uses_each_column_once():
    cols = ["Symbol", "Side", "Open Time", "Close Time", "Profit", "Qty"]
    m = auto_map(cols, {"pnl": "Profit"})
    assert m["pnl"] == "Profit"
    assert m["instrument"] == "Symbol" and m["entry_time"] == "Open Time"
    assert len(set(m.values())) == len(m)
    with pytest.raises(JournalConversionError):
        auto_map(cols, {"pnl": "Nope"})


# ------------------------------------------------------------------ conversions


def test_mt4_preset_gross_pnl_signed_fees_and_risk_from_stop():
    opts = ConversionOptions.from_preset("mt4", multiplier=100_000, drop_invalid=True)
    res = convert_journal(_raw(EXAMPLES / "mt4_export.csv"), opts)
    t = res.trades.set_index("trade_id")
    assert len(t) == 5  # balance row dropped
    assert res.row_issues["line"].unique().tolist() == [5]
    # 1001: gross 280, commission -7 -> fee 7, net 273; risk |1.0851-1.0831| x 1 x 1e5 = 200
    assert t.loc["1001", "pnl"] == pytest.approx(273.0)
    assert t.loc["1001", "fees"] == pytest.approx(7.0)
    assert t.loc["1001", "risk_amount"] == pytest.approx(200.0)
    # 1003: commission -14 and swap -4.2 -> fee 18.2
    assert t.loc["1003", "pnl"] == pytest.approx(600.0 - 18.2)
    assert t.loc["1002", "direction"] == "short"


def test_generic_journal_dayfirst_money_formats_and_r_column():
    res = convert_journal(
        _raw(EXAMPLES / "generic_journal.csv"), ConversionOptions(dayfirst=True, drop_invalid=True)
    )
    t = res.trades
    assert len(t) == 5
    assert t.loc[0, "entry_time"] == pd.Timestamp("2024-03-04", tz="UTC")
    assert t.loc[1, "pnl"] == pytest.approx(-320.5)
    assert t.loc[0, "risk_amount"] == pytest.approx(1250 / 1.25)  # from R column
    assert t["trade_id"].str.startswith("J").all()  # generated
    assert (t["exit_time"] == t["entry_time"]).all()  # date-only journal


def test_invalid_rows_fail_unless_dropped():
    with pytest.raises(JournalConversionError) as exc:
        convert_journal(_raw(EXAMPLES / "generic_journal.csv"), ConversionOptions(dayfirst=True))
    issues = exc.value.result.row_issues
    assert issues.to_dict("records") == [{"line": 6, "problem": "direction not recognised"}]


def test_signed_size_and_pnl_derived_from_prices():
    raw = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB"],
            "Opened": ["2024-01-02 10:00", "2024-01-03 11:00"],
            "Closed": ["2024-01-02 15:00", "2024-01-03 12:00"],
            "Open Price": ["10", "20"],
            "Close Price": ["12", "19"],
            "Quantity": ["100", "-50"],
            "Commission": ["1", "1"],
        }
    )
    res = convert_journal(raw, ConversionOptions(timezone="America/New_York"))
    t = res.trades
    assert t["direction"].tolist() == ["long", "short"]
    assert t["size"].tolist() == [100.0, 50.0]
    # long: (12-10) x 100 - 1 = 199; short: -(19-20) x 50 - 1 = 49
    assert t["pnl"].tolist() == pytest.approx([199.0, 49.0])
    assert t.loc[0, "entry_time"] == pd.Timestamp("2024-01-02 15:00", tz="UTC")  # EST -> UTC


def test_missing_required_field_gives_actionable_error():
    raw = pd.DataFrame({"Symbol": ["A"], "Profit": ["1"]})
    with pytest.raises(JournalConversionError, match="could not find or derive"):
        convert_journal(raw)


def test_canonical_journal_round_trips_unchanged():
    raw = _raw(TESTING_JOURNAL)
    res = convert_journal(raw, ConversionOptions(fee_columns=[]))
    original = pd.read_csv(TESTING_JOURNAL)
    assert len(res.trades) == len(original)
    np.testing.assert_allclose(res.trades["pnl"], original["pnl"])
    assert res.trades["trade_id"].tolist() == original["trade_id"].tolist()


# ------------------------------------------------------------------ CLI


def test_cli_check_and_convert(tmp_path, capsys):
    assert main(["check", str(TESTING_JOURNAL)]) == 0
    assert main(["check", str(EXAMPLES / "generic_journal.csv")]) == 1
    out = tmp_path / "g.csv"
    code = main(
        [
            "convert",
            str(EXAMPLES / "generic_journal.csv"),
            "--dayfirst",
            "--drop-invalid",
            "-o",
            str(out),
        ]
    )
    assert code == 0 and out.exists() and out.with_suffix(".conversion.md").exists()
    assert main(["check", str(out)]) == 0


def test_cli_mapping_template_round_trip(tmp_path):
    m = tmp_path / "map.json"
    assert main(["convert", str(EXAMPLES / "generic_journal.csv"), "--write-mapping", str(m)]) == 0
    cfg = json.loads(m.read_text())
    cfg["dayfirst"] = True
    m.write_text(json.dumps(cfg))
    out = tmp_path / "g.csv"
    code = main(
        [
            "convert",
            str(EXAMPLES / "generic_journal.csv"),
            "--mapping",
            str(m),
            "--drop-invalid",
            "-o",
            str(out),
        ]
    )
    assert code == 0
