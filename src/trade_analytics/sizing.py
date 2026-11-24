"""Kelly position sizing with parameter uncertainty.

Kelly (1956) chooses the size scale f that maximises expected log growth:

    g(f) = E[ log(1 + f * x) ]

For a binary bet winning b with probability p and losing 1 otherwise,
f* = p - (1 - p) / b. For general outcomes we maximise g(f) numerically over
0 <= f < 1 / |min x| (beyond that one bad trade wipes out the account).

The estimate of f* inherits all the sampling error of the outcomes. We
propagate it with the Bayesian bootstrap: for each Dirichlet weight draw w,
maximise sum_i w_i log(1 + f x_i). The spread of f* across draws shows why
practitioners bet a fraction (1/4 to 1/2) of the point-estimate Kelly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy.optimize import minimize_scalar


def growth_rate(
    outcomes: npt.ArrayLike, fraction: float, weights: np.ndarray | None = None
) -> float:
    x = np.asarray(outcomes, dtype=float)
    g = 1.0 + fraction * x
    if np.any(g <= 0):
        return float("-inf")
    logs = np.log(g)
    return float(np.average(logs, weights=weights))


def _f_max(x: np.ndarray) -> float:
    worst = x.min()
    return (1.0 / -worst) * (1 - 1e-9) if worst < 0 else 100.0


def kelly_fraction(outcomes: npt.ArrayLike, weights: np.ndarray | None = None) -> float:
    """Growth-optimal size scale (0 if the weighted mean outcome is <= 0)."""
    x = np.asarray(outcomes, dtype=float)
    mean = np.average(x, weights=weights)
    if mean <= 0:
        return 0.0
    res = minimize_scalar(
        lambda f: -growth_rate(x, f, weights),
        bounds=(0.0, _f_max(x)),
        method="bounded",
        options={"xatol": 1e-8},
    )
    return float(res.x)


@dataclass(frozen=True)
class KellyUncertainty:
    point: float
    draws: np.ndarray

    def quantile(self, q: float) -> float:
        return float(np.quantile(self.draws, q))

    @property
    def prob_zero(self) -> float:
        """Posterior probability that the growth-optimal size is zero (no edge)."""
        return float(np.mean(self.draws == 0.0))


def kelly_with_uncertainty(
    outcomes: npt.ArrayLike, n_draws: int = 2_000, seed: int | None = 0
) -> KellyUncertainty:
    x = np.asarray(outcomes, dtype=float)
    rng = np.random.default_rng(seed)
    w = rng.dirichlet(np.ones(x.size), size=n_draws)
    draws = np.array([kelly_fraction(x, wi) for wi in w])
    return KellyUncertainty(point=kelly_fraction(x), draws=draws)
