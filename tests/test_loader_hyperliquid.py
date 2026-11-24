"""Fill-to-trade reconstruction on small hand-built fill sequences."""

import pandas as pd
import pytest

from trade_analytics.loaders.hyperliquid import reconstruct_trades


def _fills(rows):
    t0 = pd.Timestamp("2025-01-01 00:00", tz="UTC")
    cols = [
        "coin",
        "minute",
        "price",
        "qty",
        "side",
        "start_position",
        "closed_pnl",
        "fee",
        "label",
    ]
    df = pd.DataFrame(rows, columns=cols)
    df["time"] = t0 + pd.to_timedelta(df["minute"], unit="min")
    df["direction_label"] = df.pop("label")
    df["source_row"] = range(len(df))
    df["account"] = "acct"
    return df


def test_scale_in_then_out_long():
    f = _fills(
        [
            ("BTC", 0, 100.0, 1.0, 1, 0.0, 0.0, 0.1, "Open Long"),
            ("BTC", 1, 110.0, 1.0, 1, 1.0, 0.0, 0.1, "Open Long"),
            ("BTC", 2, 120.0, 2.0, -1, 2.0, 30.0, 0.2, "Close Long"),
        ]
    )
    trades, diag = reconstruct_trades(f)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["direction"] == "long"
    assert t["entry_price"] == pytest.approx(105.0)  # VWAP of entries
    assert t["exit_price"] == pytest.approx(120.0)
    assert t["size"] == pytest.approx(2.0)
    assert t["pnl"] == pytest.approx(30.0 - 0.4)  # closed pnl net of all fees
    assert t["price_pnl"] == pytest.approx(30.0)


def test_flip_is_split_into_two_trades():
    f = _fills(
        [
            ("ETH", 0, 10.0, 3.0, 1, 0.0, 0.0, 0.3, "Open Long"),
            # sells 5: closes 3 long, opens 2 short; fee 0.5 split 0.3 / 0.2
            ("ETH", 1, 12.0, 5.0, -1, 3.0, 6.0, 0.5, "Long > Short"),
            ("ETH", 2, 11.0, 2.0, 1, -2.0, 2.0, 0.2, "Close Short"),
        ]
    )
    trades, diag = reconstruct_trades(f)
    assert diag["flips_split"] == 1
    assert list(trades["direction"]) == ["long", "short"]
    assert trades.loc[0, "pnl"] == pytest.approx(6.0 - 0.3 - 0.3)
    assert trades.loc[1, "entry_price"] == pytest.approx(12.0)
    assert trades.loc[1, "pnl"] == pytest.approx(2.0 - 0.2 - 0.2)


def test_gap_discards_open_trade_and_skips_until_flat():
    f = _fills(
        [
            ("BTC", 0, 100.0, 1.0, 1, 0.0, 0.0, 0.0, "Open Long"),
            # start position should be 1.0 -> gap in data
            ("BTC", 1, 101.0, 1.0, -1, 5.0, 1.0, 0.0, "Close Long"),
            ("BTC", 2, 102.0, 4.0, -1, 4.0, 8.0, 0.0, "Close Long"),
            ("BTC", 3, 100.0, 1.0, -1, 0.0, 0.0, 0.0, "Open Short"),
            ("BTC", 4, 99.0, 1.0, 1, -1.0, 1.0, 0.0, "Close Short"),
        ]
    )
    trades, diag = reconstruct_trades(f)
    assert diag["gaps_discarded"] == 1
    assert diag["skipped_until_flat"] == 2
    assert len(trades) == 1 and trades.loc[0, "direction"] == "short"
