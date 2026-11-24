"""Sharpe-ratio statistics for a track record.

* Per-trade Sharpe ratio SR = mean / std.
* Standard error under iid normal returns (Lo 2002): sqrt((1 + SR^2 / 2) / n).
* Probabilistic Sharpe Ratio (Bailey & López de Prado 2012): probability that
  the true SR exceeds a benchmark SR*, accounting for skewness and kurtosis:

      PSR = Phi( (SR - SR*) * sqrt(n - 1) / sqrt(1 - g3*SR + (g4 - 1)/4 * SR^2) )

  g3 = skewness, g4 = kurtosis (non-excess; 3 for a normal distribution).
* Minimum Track Record Length: the number of trades needed for PSR to reach
  1 - alpha given the observed SR, skew and kurtosis:

      MinTRL = 1 + (1 - g3*SR + (g4 - 1)/4 * SR^2) * (z_{1-alpha} / (SR - SR*))^2

All quantities are *per trade*; they are not annualised because trades are not
equally spaced in time.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy import stats


def sharpe_ratio(outcomes: npt.ArrayLike) -> float:
    x = np.asarray(outcomes, dtype=float)
    return float(x.mean() / x.std(ddof=1))


def sharpe_se_iid(sr: float, n: int) -> float:
    """Lo (2002) standard error of the Sharpe ratio under iid normal returns."""
    return float(np.sqrt((1.0 + 0.5 * sr**2) / n))


def _moments(x: np.ndarray) -> tuple[float, float, float]:
    sr = float(x.mean() / x.std(ddof=1))
    skew = float(stats.skew(x, bias=False))
    kurt = float(stats.kurtosis(x, fisher=False, bias=False))  # non-excess
    return sr, skew, kurt


def probabilistic_sharpe_ratio(outcomes: npt.ArrayLike, sr_benchmark: float = 0.0) -> float:
    x = np.asarray(outcomes, dtype=float)
    n = x.size
    sr, g3, g4 = _moments(x)
    denom = 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr**2
    return float(stats.norm.cdf((sr - sr_benchmark) * np.sqrt(n - 1) / np.sqrt(denom)))


def min_track_record_length(
    outcomes: npt.ArrayLike, sr_benchmark: float = 0.0, alpha: float = 0.05
) -> float:
    x = np.asarray(outcomes, dtype=float)
    sr, g3, g4 = _moments(x)
    if sr <= sr_benchmark:
        return float("inf")
    z = stats.norm.ppf(1.0 - alpha)
    return float(1.0 + (1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr**2) * (z / (sr - sr_benchmark)) ** 2)


@dataclass(frozen=True)
class SharpeSummary:
    n: int
    sharpe: float
    se_iid: float
    skew: float
    kurtosis: float
    psr: float
    min_trl: float


def sharpe_summary(outcomes: npt.ArrayLike, sr_benchmark: float = 0.0) -> SharpeSummary:
    x = np.asarray(outcomes, dtype=float)
    sr, g3, g4 = _moments(x)
    return SharpeSummary(
        n=int(x.size),
        sharpe=sr,
        se_iid=sharpe_se_iid(sr, x.size),
        skew=g3,
        kurtosis=g4,
        psr=probabilistic_sharpe_ratio(x, sr_benchmark),
        min_trl=min_track_record_length(x, sr_benchmark),
    )
