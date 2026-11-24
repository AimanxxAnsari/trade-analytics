"""Monte Carlo of the trade sequence: drawdowns and risk of ruin.

The historical order of trades is one draw from many possible orders. We
resample outcomes (iid or in blocks) to build many equity paths and read off
the distribution of maximum drawdown and the probability of hitting a loss
threshold ("ruin").

Sizing convention: each trade multiplies equity by (1 + f * x), where x is the
trade outcome and f the position-size scale:

* x in R-multiples   -> f is the fraction of equity risked per trade;
* x = return on notional -> f is leverage (notional / equity).

If f * x <= -1 the account is wiped out on that trade.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

from trade_analytics.bootstrap import default_block_length, stationary_indices


def simulate_equity(
    outcomes: npt.ArrayLike,
    fraction: float,
    n_paths: int = 10_000,
    n_trades: int | None = None,
    method: str = "iid",
    block_length: float | None = None,
    seed: int | None = 0,
) -> np.ndarray:
    """Equity paths of shape (n_paths, n_trades + 1), starting at 1.0."""
    x = np.asarray(outcomes, dtype=float)
    n = n_trades or x.size
    rng = np.random.default_rng(seed)
    if method == "iid":
        idx = rng.integers(0, x.size, (n_paths, n))
    elif method == "stationary":
        if n != x.size:
            raise ValueError("stationary resampling keeps the sample length")
        idx = stationary_indices(x.size, n_paths, block_length or default_block_length(n), rng)
    else:
        raise ValueError(f"unknown method {method!r}")
    growth = np.maximum(1.0 + fraction * x[idx], 0.0)  # wiped out -> 0
    paths = np.cumprod(growth, axis=1)
    return np.hstack([np.ones((n_paths, 1)), paths])


def max_drawdown(paths: np.ndarray) -> np.ndarray:
    """Maximum peak-to-trough decline of each path, as a positive fraction."""
    paths = np.atleast_2d(paths)
    peaks = np.maximum.accumulate(paths, axis=1)
    return np.max(1.0 - paths / peaks, axis=1)


@dataclass(frozen=True)
class DrawdownRisk:
    table: pd.DataFrame  # rows: fraction; columns: P(maxDD >= threshold), median DD, etc.


def drawdown_risk(
    outcomes: npt.ArrayLike,
    fractions: list[float],
    thresholds: tuple[float, ...] = (0.2, 0.3, 0.5),
    ruin_level: float = 0.5,
    n_paths: int = 10_000,
    method: str = "iid",
    seed: int | None = 0,
) -> DrawdownRisk:
    """Drawdown and ruin statistics for several position-size scales.

    Ruin = equity falls to ``ruin_level`` (default: losing half the account) or
    below at any point.
    """
    rows = []
    for f in fractions:
        paths = simulate_equity(outcomes, f, n_paths=n_paths, method=method, seed=seed)
        dd = max_drawdown(paths)
        row = {
            "fraction": f,
            "median_final_equity": float(np.median(paths[:, -1])),
            "median_max_dd": float(np.median(dd)),
            "p95_max_dd": float(np.quantile(dd, 0.95)),
            "p_ruin": float(np.mean(paths.min(axis=1) <= ruin_level)),
        }
        for t in thresholds:
            row[f"p_dd_ge_{int(t * 100)}"] = float(np.mean(dd >= t))
        rows.append(row)
    return DrawdownRisk(pd.DataFrame(rows))
