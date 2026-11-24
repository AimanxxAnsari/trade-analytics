"""Bootstrap inference on the mean trade outcome.

Two resampling schemes:

* **iid bootstrap** (Efron 1979): resample trades with replacement. Valid if
  outcomes are independent.
* **stationary bootstrap** (Politis & Romano 1994): resample *blocks* of
  consecutive trades with random (geometric) lengths, preserving short-range
  serial dependence such as streaks or volatility clustering.

The confidence interval is the percentile interval of the bootstrap means.
The one-sided p-value for H0: mean <= 0 vs H1: mean > 0 uses the bootstrap
distribution *shifted* to have mean zero (imposing the null).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt

Method = Literal["iid", "stationary"]


@dataclass(frozen=True)
class BootstrapResult:
    mean: float
    ci_low: float
    ci_high: float
    ci_level: float
    p_value: float  # one-sided, H1: mean > 0
    method: str
    block_length: float | None
    n_boot: int
    samples: np.ndarray  # bootstrap means


def stationary_indices(
    n: int, size: int, block_length: float, rng: np.random.Generator
) -> np.ndarray:
    """Index matrix (size x n) for the Politis–Romano stationary bootstrap.

    Each resampled series starts at a random position; at every step it either
    continues to the next trade (probability 1 - 1/L) or jumps to a new random
    start (probability 1/L). Indices wrap around the end of the sample.
    """
    if block_length < 1:
        raise ValueError("block_length must be >= 1")
    p_new = 1.0 / block_length
    idx = np.empty((size, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, size)
    new_block = rng.random((size, n)) < p_new
    random_starts = rng.integers(0, n, (size, n))
    for t in range(1, n):
        idx[:, t] = np.where(new_block[:, t], random_starts[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def default_block_length(n: int) -> float:
    """Simple rule of thumb L ~ n^(1/3) (Politis & White 2004 give a data-driven choice)."""
    return max(1.0, n ** (1.0 / 3.0))


def bootstrap_mean(
    outcomes: npt.ArrayLike,
    n_boot: int = 10_000,
    ci_level: float = 0.95,
    method: Method = "iid",
    block_length: float | None = None,
    seed: int | None = 0,
) -> BootstrapResult:
    """Bootstrap the mean outcome: percentile CI and one-sided p-value."""
    x = np.asarray(outcomes, dtype=float)
    n = x.size
    if n < 2:
        raise ValueError("need at least 2 outcomes")
    rng = np.random.default_rng(seed)

    if method == "iid":
        idx = rng.integers(0, n, (n_boot, n))
        block_length = None
    elif method == "stationary":
        block_length = block_length or default_block_length(n)
        idx = stationary_indices(n, n_boot, block_length, rng)
    else:
        raise ValueError(f"unknown method {method!r}")

    means = x[idx].mean(axis=1)
    mean = float(x.mean())
    alpha = 1.0 - ci_level
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])

    # Impose H0 (mean = 0) by centring the bootstrap distribution, then ask how
    # often a mean at least as large as the observed one appears.
    null_means = means - mean
    p_value = float((np.sum(null_means >= mean) + 1) / (n_boot + 1))

    return BootstrapResult(
        mean=mean,
        ci_low=float(lo),
        ci_high=float(hi),
        ci_level=ci_level,
        p_value=p_value,
        method=method,
        block_length=block_length,
        n_boot=n_boot,
        samples=means,
    )
