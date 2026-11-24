"""Canonical trade-table schema and validation.

Every analysis in this package consumes a DataFrame that passes :func:`validate_trades`.
The raw broker/journal export is mapped onto this schema by a loader (added once the
real export format is known); see ``docs/design/trade-schema.md``.
"""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS: dict[str, str] = {
    "trade_id": "unique identifier",
    "instrument": "e.g. SPX500, BRENT, XAUUSD, EURUSD",
    "direction": "'long' or 'short'",
    "entry_time": "timestamp (timezone-aware, UTC)",
    "exit_time": "timestamp (timezone-aware, UTC)",
    "entry_price": "float > 0",
    "exit_price": "float > 0",
    "size": "float > 0 (units / lots / contracts)",
    "pnl": "realised P&L in account currency, net of fees",
}

OPTIONAL_COLUMNS: dict[str, str] = {
    "risk_amount": "planned loss at the stop, account currency, > 0 (needed for R-multiples)",
    "stop_price": "initial stop price",
    "fees": "commissions + financing, account currency",
    "setup": "setup / strategy tag",
}

VALID_DIRECTIONS = frozenset({"long", "short"})


class TradeSchemaError(ValueError):
    """Raised when a trade table violates the canonical schema."""


def validate_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """Validate a trade table against the canonical schema.

    Returns the input unchanged if valid; raises :class:`TradeSchemaError` listing
    every problem found (not just the first) otherwise.
    """
    problems: list[str] = []

    missing = [c for c in REQUIRED_COLUMNS if c not in trades.columns]
    if missing:
        raise TradeSchemaError(f"missing required columns: {missing}")

    if trades.empty:
        raise TradeSchemaError("trade table is empty")

    if trades["trade_id"].duplicated().any():
        dupes = trades.loc[trades["trade_id"].duplicated(), "trade_id"].tolist()
        problems.append(f"duplicate trade_id values: {dupes[:10]}")

    bad_dir = ~trades["direction"].isin(VALID_DIRECTIONS)
    if bad_dir.any():
        problems.append(
            f"invalid direction in {int(bad_dir.sum())} rows (allowed: {sorted(VALID_DIRECTIONS)})"
        )

    for col in ("entry_time", "exit_time"):
        if not pd.api.types.is_datetime64_any_dtype(trades[col]):
            problems.append(f"{col} must be a datetime column")
        elif trades[col].dt.tz is None:
            problems.append(f"{col} must be timezone-aware (UTC)")

    if not problems:
        backwards = trades["exit_time"] < trades["entry_time"]
        if backwards.any():
            problems.append(f"exit_time before entry_time in {int(backwards.sum())} rows")

    for col in ("entry_price", "exit_price", "size"):
        if not pd.api.types.is_numeric_dtype(trades[col]):
            problems.append(f"{col} must be numeric")
        elif (trades[col] <= 0).any():
            problems.append(f"{col} must be > 0")

    if not pd.api.types.is_numeric_dtype(trades["pnl"]):
        problems.append("pnl must be numeric")
    elif trades["pnl"].isna().any():
        problems.append("pnl has missing values")

    if "risk_amount" in trades.columns:
        risk = trades["risk_amount"].dropna()
        if (risk <= 0).any():
            problems.append("risk_amount must be > 0 where present")

    if problems:
        raise TradeSchemaError("; ".join(problems))
    return trades
