"""Reconstruct round-trip trades from Hyperliquid perpetual-futures fills.

Source: the public "Historical Trade Data" dataset of Hyperliquid fills (Kaggle,
CC0 1.0). Each row is one *fill*; a trade journal needs *round trips* (flat ->
position -> flat). See ``docs/design/fill-reconstruction.md``.

Algorithm (per account and coin, fills in time order):

* A trade opens on a fill whose ``Start Position`` is flat.
* Fills that increase |position| in the trade direction are entry fills;
  fills that reduce it are exit fills.
* The trade closes when the position returns to flat.
* A fill that flips the position (long -> short) is split: the part that
  closes the old position belongs to the old trade, the remainder opens a new
  trade at the same price and time. Fees are split pro rata.
* If a fill's ``Start Position`` does not match the running position (a gap in
  the data), the open trade is discarded rather than guessed.
* Positions already open when the data starts are skipped until flat.

Net P&L per trade = sum of ``Closed PnL`` - sum of fees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

PERP_DIRECTIONS = frozenset(
    {
        "Open Long",
        "Close Long",
        "Open Short",
        "Close Short",
        "Long > Short",
        "Short > Long",
        "Liquidated Isolated Short",
        "Liquidated Isolated Long",
        "Auto-Deleveraging",
    }
)

SOURCE_TIMEZONE = "Asia/Kolkata"  # the dataset's "Timestamp IST" column


def load_fills(path: str | Path, account: str | None = None) -> pd.DataFrame:
    """Read the raw CSV and return normalised perpetual-futures fills.

    Spot fills (coins named ``@n`` or ``X/Y``) and non-trade events are dropped.
    Times are converted from IST to UTC. Original row order is kept as a
    tie-breaker because timestamps only have minute resolution.
    """
    raw = pd.read_csv(path)
    if account is not None:
        raw = raw[raw["Account"] == account]

    is_perp = ~raw["Coin"].str.startswith("@") & ~raw["Coin"].str.contains("/", regex=False)
    raw = raw[is_perp & raw["Direction"].isin(PERP_DIRECTIONS)].copy()

    time = pd.to_datetime(raw["Timestamp IST"], format="%d-%m-%Y %H:%M")
    fills = pd.DataFrame(
        {
            "account": raw["Account"].to_numpy(),
            "coin": raw["Coin"].to_numpy(),
            "time": time.dt.tz_localize(SOURCE_TIMEZONE).dt.tz_convert("UTC").to_numpy(),
            "price": raw["Execution Price"].to_numpy(dtype=float),
            "qty": raw["Size Tokens"].to_numpy(dtype=float),
            "side": np.where(raw["Side"].to_numpy() == "BUY", 1, -1),
            "start_position": raw["Start Position"].to_numpy(dtype=float),
            "closed_pnl": raw["Closed PnL"].to_numpy(dtype=float),
            "fee": raw["Fee"].to_numpy(dtype=float),
            "direction_label": raw["Direction"].to_numpy(),
            "source_row": raw.index.to_numpy(),
        }
    )
    fills["time"] = pd.to_datetime(fills["time"], utc=True)
    return fills.sort_values(["time", "source_row"], kind="stable").reset_index(drop=True)


@dataclass
class _OpenTrade:
    coin: str
    sign: int  # +1 long, -1 short
    entry_time: pd.Timestamp
    entry_qty: float = 0.0
    entry_notional: float = 0.0
    exit_qty: float = 0.0
    exit_notional: float = 0.0
    closed_pnl: float = 0.0
    fees: float = 0.0
    max_position: float = 0.0
    n_fills: int = 0
    exit_time: pd.Timestamp | None = None
    liquidated: bool = False
    labels: set[str] = field(default_factory=set)

    def add_entry(self, qty: float, price: float, fee: float, time: pd.Timestamp) -> None:
        self.entry_qty += qty
        self.entry_notional += qty * price
        self.fees += fee
        self.n_fills += 1
        self.max_position = max(self.max_position, self.entry_qty - self.exit_qty)
        self.exit_time = time

    def add_exit(self, qty: float, price: float, pnl: float, fee: float, time) -> None:
        self.exit_qty += qty
        self.exit_notional += qty * price
        self.closed_pnl += pnl
        self.fees += fee
        self.n_fills += 1
        self.exit_time = time


def _is_flat(position: float, scale: float) -> bool:
    return abs(position) <= 1e-9 + 1e-6 * scale


def reconstruct_trades(fills: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Turn fills into canonical round-trip trades.

    Returns ``(trades, diagnostics)``. ``trades`` follows the canonical schema
    (plus ``fees``, ``notional``, ``max_position``, ``n_fills``, ``liquidated``,
    ``price_pnl``); diagnostics count discarded and skipped trades.
    """
    records: list[dict] = []
    diag = {"fills": len(fills), "gaps_discarded": 0, "skipped_until_flat": 0, "flips_split": 0}

    for coin, g in fills.groupby("coin", sort=True):
        trade: _OpenTrade | None = None
        expected: float | None = None  # running position after the previous fill
        for row in g.itertuples(index=False):
            start, qty, side = row.start_position, row.qty, row.side
            end = start + side * qty
            scale = max(abs(start), qty, 1.0)

            # Continuity check: a gap in the data invalidates the open trade.
            if expected is not None and not _is_flat(start - expected, scale):
                if trade is not None:
                    diag["gaps_discarded"] += 1
                trade = None
            expected = end

            if trade is None:
                if not _is_flat(start, scale):
                    diag["skipped_until_flat"] += 1
                    continue
                if _is_flat(end, scale):
                    continue  # zero-size or self-cancelling fill
                trade = _OpenTrade(coin=coin, sign=int(np.sign(end)), entry_time=row.time)

            trade.labels.add(row.direction_label)
            if "Liquidated" in row.direction_label:
                trade.liquidated = True

            same_dir = side == trade.sign
            if same_dir:
                trade.add_entry(qty, row.price, row.fee, row.time)
                continue

            # Reducing fill: may close, partially close, or flip.
            closing_qty = min(qty, abs(start))
            flip_qty = qty - closing_qty
            fee_close = row.fee * closing_qty / qty if qty else 0.0
            trade.add_exit(closing_qty, row.price, row.closed_pnl, fee_close, row.time)

            if _is_flat(end, scale) or flip_qty > 1e-9 + 1e-6 * scale:
                records.append(_finish(trade))
                trade = None
                if flip_qty > 1e-9 + 1e-6 * scale:
                    diag["flips_split"] += 1
                    trade = _OpenTrade(coin=coin, sign=side, entry_time=row.time)
                    trade.add_entry(flip_qty, row.price, row.fee - fee_close, row.time)

    trades = pd.DataFrame.from_records(records)
    if trades.empty:
        return trades, diag
    trades = trades.sort_values(["entry_time", "instrument"], kind="stable").reset_index(drop=True)
    trades.insert(0, "trade_id", [f"T{i + 1:04d}" for i in range(len(trades))])
    diag["trades"] = len(trades)
    return trades, diag


def _finish(t: _OpenTrade) -> dict:
    entry_price = t.entry_notional / t.entry_qty
    exit_price = t.exit_notional / t.exit_qty
    return {
        "instrument": t.coin,
        "direction": "long" if t.sign > 0 else "short",
        "entry_time": t.entry_time,
        "exit_time": t.exit_time,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "size": t.entry_qty,
        "pnl": t.closed_pnl - t.fees,
        "fees": t.fees,
        "price_pnl": t.sign * (exit_price - entry_price) * t.exit_qty,
        "notional": entry_price * t.entry_qty,
        "max_position": t.max_position,
        "n_fills": t.n_fills,
        "liquidated": t.liquidated,
    }
