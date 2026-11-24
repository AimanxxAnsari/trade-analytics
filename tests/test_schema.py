import pandas as pd
import pytest

from trade_analytics import TradeSchemaError, validate_trades


def _valid() -> pd.DataFrame:
    """Synthetic trades only — real trades never appear in tests (ADR-0001)."""
    t0 = pd.Timestamp("2025-01-02 09:00", tz="UTC")
    return pd.DataFrame(
        {
            "trade_id": ["T1", "T2"],
            "instrument": ["SYN_A", "SYN_B"],
            "direction": ["long", "short"],
            "entry_time": [t0, t0 + pd.Timedelta(hours=1)],
            "exit_time": [t0 + pd.Timedelta(hours=2), t0 + pd.Timedelta(hours=3)],
            "entry_price": [100.0, 50.0],
            "exit_price": [101.0, 51.0],
            "size": [1.0, 2.0],
            "pnl": [1.0, -2.0],
            "risk_amount": [0.5, 1.0],
        }
    )


def test_valid_table_passes():
    df = _valid()
    assert validate_trades(df) is df


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.drop(columns="pnl"), "missing required columns"),
        (lambda d: d.assign(trade_id=["T1", "T1"]), "duplicate trade_id"),
        (lambda d: d.assign(direction=["long", "sideways"]), "invalid direction"),
        (lambda d: d.assign(size=[1.0, 0.0]), "size must be > 0"),
        (lambda d: d.assign(risk_amount=[0.5, -1.0]), "risk_amount must be > 0"),
        (
            lambda d: d.assign(exit_time=d["entry_time"] - pd.Timedelta(minutes=1)),
            "exit_time before entry_time",
        ),
        (
            lambda d: d.assign(entry_time=d["entry_time"].dt.tz_localize(None)),
            "timezone-aware",
        ),
    ],
)
def test_invalid_tables_fail(mutate, message):
    with pytest.raises(TradeSchemaError, match=message):
        validate_trades(mutate(_valid()))


def test_reports_all_problems_at_once():
    bad = _valid().assign(direction=["up", "down"], size=[0.0, 1.0])
    with pytest.raises(TradeSchemaError) as exc:
        validate_trades(bad)
    assert "invalid direction" in str(exc.value)
    assert "size must be > 0" in str(exc.value)
