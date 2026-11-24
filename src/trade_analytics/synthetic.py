"""Synthetic trade generators with *known* properties, for tests and demos.

Real data never tells you the true edge; synthetic data does. Every inference
method in this package is checked here first (known-answer tests).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def binary_outcomes(
    n: int, win_rate: float, win_r: float, loss_r: float = 1.0, seed: int | None = 0
) -> np.ndarray:
    """R-multiples that are +win_r with probability win_rate, otherwise -loss_r."""
    rng = np.random.default_rng(seed)
    return np.where(rng.random(n) < win_rate, win_r, -loss_r)


def t_outcomes(n: int, mean: float, scale: float, df: float = 4.0, seed: int | None = 0):
    """Fat-tailed outcomes: Student-t with ``df`` degrees of freedom, shifted to ``mean``."""
    rng = np.random.default_rng(seed)
    return mean + scale * rng.standard_t(df, n)


def synthetic_trades(outcomes_r: np.ndarray, seed: int | None = 0) -> pd.DataFrame:
    """Canonical trade table whose R-multiples equal ``outcomes_r`` (risk_amount = 100)."""
    rng = np.random.default_rng(seed)
    n = len(outcomes_r)
    start = pd.Timestamp("2024-01-01", tz="UTC")
    entry = start + pd.to_timedelta(np.sort(rng.uniform(0, 365, n)), unit="D")
    exit_ = entry + pd.to_timedelta(rng.uniform(0.01, 3, n), unit="D")
    direction = np.where(rng.random(n) < 0.5, "long", "short")
    entry_price = 100 * np.exp(rng.normal(0, 0.1, n))
    risk = 100.0
    pnl = np.asarray(outcomes_r) * risk
    size = np.full(n, 10.0)
    sign = np.where(direction == "long", 1, -1)
    exit_price = entry_price + sign * pnl / size
    return pd.DataFrame(
        {
            "trade_id": [f"S{i + 1:04d}" for i in range(n)],
            "instrument": rng.choice(["SYN_A", "SYN_B"], n),
            "direction": direction,
            "entry_time": entry,
            "exit_time": exit_,
            "entry_price": entry_price,
            "exit_price": np.maximum(exit_price, 1e-6),
            "size": size,
            "pnl": pnl,
            "risk_amount": risk,
        }
    )
