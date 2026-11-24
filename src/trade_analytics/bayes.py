"""Bayesian assessment of the edge.

* **Beta-Binomial win rate.** With a Beta(a, b) prior and w wins in n trades the
  posterior is Beta(a + w, b + n - w). We report the probability that the true
  win rate exceeds the breakeven win rate implied by the payoff ratio,
  p* = 1 / (1 + payoff).
* **Bayesian bootstrap** (Rubin 1981) for the mean outcome: draw Dirichlet(1,...,1)
  weights over trades; each weighted mean is a draw from the posterior of the
  mean under a non-parametric model. Gives P(mean > 0) directly.
* **Partial pooling across groups** (empirical Bayes Beta-Binomial): fit a Beta
  prior to the group win rates by the method of moments, then shrink each
  group's rate towards the overall rate in proportion to how little data it
  has. Guards against over-reading small slices.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy import stats


@dataclass(frozen=True)
class BetaPosterior:
    alpha: float
    beta: float

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def interval(self, level: float = 0.95) -> tuple[float, float]:
        lo, hi = stats.beta.ppf([(1 - level) / 2, (1 + level) / 2], self.alpha, self.beta)
        return float(lo), float(hi)

    def prob_above(self, threshold: float) -> float:
        return float(stats.beta.sf(threshold, self.alpha, self.beta))


def win_rate_posterior(
    wins: int, n: int, prior_alpha: float = 1.0, prior_beta: float = 1.0
) -> BetaPosterior:
    if not 0 <= wins <= n:
        raise ValueError("need 0 <= wins <= n")
    return BetaPosterior(prior_alpha + wins, prior_beta + n - wins)


def breakeven_win_rate(payoff_ratio: float) -> float:
    """Win rate at which expectancy is zero for a given payoff ratio (no scratches)."""
    return 1.0 / (1.0 + payoff_ratio)


def bayesian_bootstrap_mean(
    outcomes: npt.ArrayLike, n_draws: int = 10_000, seed: int | None = 0
) -> np.ndarray:
    """Posterior draws of the mean outcome (Rubin 1981)."""
    x = np.asarray(outcomes, dtype=float)
    rng = np.random.default_rng(seed)
    w = rng.dirichlet(np.ones(x.size), size=n_draws)
    return w @ x


@dataclass(frozen=True)
class PooledRates:
    groups: list[str]
    n: np.ndarray
    raw: np.ndarray
    pooled: np.ndarray
    prior_alpha: float
    prior_beta: float


def partial_pool_win_rates(groups: list[str], wins: npt.ArrayLike, n: npt.ArrayLike) -> PooledRates:
    """Empirical-Bayes shrinkage of group win rates (method-of-moments Beta prior)."""
    wins = np.asarray(wins, dtype=float)
    n = np.asarray(n, dtype=float)
    if wins.size < 2:
        raise ValueError("need at least two groups to pool")
    raw = wins / n
    m = np.average(raw, weights=n)
    # Between-group variance net of the binomial sampling variance.
    v_total = np.average((raw - m) ** 2, weights=n)
    v_sampling = np.mean(m * (1 - m) / n)
    v_between = max(v_total - v_sampling, 1e-6)
    # Beta(a, b) with mean m and variance v_between.
    k = max(m * (1 - m) / v_between - 1.0, 1e-3)  # k = a + b ("prior sample size")
    a, b = m * k, (1 - m) * k
    pooled = (a + wins) / (a + b + n)
    return PooledRates(list(groups), n, raw, pooled, float(a), float(b))
