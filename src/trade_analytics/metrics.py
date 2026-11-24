"""Descriptive performance statistics for a sequence of trade outcomes.

All functions take outcomes in R-multiples (P&L divided by planned risk) or in
currency; the maths is the same. Conventions (see docs/decisions/ADR-0003):

* a trade with outcome > 0 is a win, < 0 a loss, == 0 a scratch;
* scratches count in the denominator of win rate and in expectancy, but not in
  the averages of wins / losses.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

ArrayLike = npt.ArrayLike


def _as_array(outcomes: ArrayLike) -> np.ndarray:
    arr = np.asarray(outcomes, dtype=float)
    if arr.ndim != 1:
        raise ValueError("outcomes must be one-dimensional")
    if arr.size == 0:
        raise ValueError("outcomes must not be empty")
    if not np.all(np.isfinite(arr)):
        raise ValueError("outcomes must be finite")
    return arr


def r_multiples(trades: pd.DataFrame) -> pd.Series:
    """P&L of each trade divided by its planned risk (``risk_amount``)."""
    if "risk_amount" not in trades.columns:
        raise ValueError("risk_amount column is required to compute R-multiples")
    if trades["risk_amount"].isna().any():
        raise ValueError("risk_amount missing for some trades")
    return (trades["pnl"] / trades["risk_amount"]).rename("r")


def win_rate(outcomes: ArrayLike) -> float:
    """Fraction of trades with a strictly positive outcome."""
    x = _as_array(outcomes)
    return float(np.mean(x > 0))


def payoff_ratio(outcomes: ArrayLike) -> float:
    """Average win divided by the absolute average loss.

    Returns ``nan`` when there are no wins or no losses.
    """
    x = _as_array(outcomes)
    wins, losses = x[x > 0], x[x < 0]
    if wins.size == 0 or losses.size == 0:
        return float("nan")
    return float(wins.mean() / abs(losses.mean()))


def profit_factor(outcomes: ArrayLike) -> float:
    """Gross profit divided by absolute gross loss (``inf`` if there are no losses)."""
    x = _as_array(outcomes)
    gross_loss = abs(x[x < 0].sum())
    gross_profit = x[x > 0].sum()
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else float("nan")
    return float(gross_profit / gross_loss)


def expectancy(outcomes: ArrayLike) -> float:
    """Mean outcome per trade.

    Identical to ``p * avg_win - q * avg_loss`` where p and q are the win and loss
    *rates* over all trades (scratches included in the denominator).
    """
    return float(_as_array(outcomes).mean())


@dataclass(frozen=True)
class PerformanceSummary:
    n_trades: int
    n_wins: int
    n_losses: int
    n_scratches: int
    win_rate: float
    avg_win: float
    avg_loss: float
    payoff_ratio: float
    profit_factor: float
    expectancy: float
    std: float
    total: float


def summarise(outcomes: ArrayLike) -> PerformanceSummary:
    """All descriptive statistics in one object."""
    x = _as_array(outcomes)
    wins, losses = x[x > 0], x[x < 0]
    return PerformanceSummary(
        n_trades=int(x.size),
        n_wins=int(wins.size),
        n_losses=int(losses.size),
        n_scratches=int(np.sum(x == 0)),
        win_rate=win_rate(x),
        avg_win=float(wins.mean()) if wins.size else float("nan"),
        avg_loss=float(losses.mean()) if losses.size else float("nan"),
        payoff_ratio=payoff_ratio(x),
        profit_factor=profit_factor(x),
        expectancy=expectancy(x),
        std=float(x.std(ddof=1)) if x.size > 1 else float("nan"),
        total=float(x.sum()),
    )
