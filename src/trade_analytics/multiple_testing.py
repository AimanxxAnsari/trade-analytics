"""Multiple-testing control when slicing a track record.

Slicing by instrument, direction, setup, month... produces many tests; some
will look significant by chance. Two standard adjustments:

* **Holm (1979)** — controls the family-wise error rate (probability of *any*
  false positive). Step-down: sort p-values ascending, multiply the k-th by
  (m - k + 1), enforce monotonicity, cap at 1.
* **Benjamini–Hochberg (1995)** — controls the false discovery rate (expected
  share of false positives among rejections). Step-up: multiply the k-th by
  m / k, enforce monotonicity from the top, cap at 1.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pandas as pd
from scipy import stats


def holm(pvalues: npt.ArrayLike) -> np.ndarray:
    p = np.asarray(pvalues, dtype=float)
    m = p.size
    order = np.argsort(p)
    adj_sorted = np.maximum.accumulate(p[order] * (m - np.arange(m)))
    out = np.empty(m)
    out[order] = np.minimum(adj_sorted, 1.0)
    return out


def benjamini_hochberg(pvalues: npt.ArrayLike) -> np.ndarray:
    p = np.asarray(pvalues, dtype=float)
    m = p.size
    order = np.argsort(p)
    ranked = p[order] * m / np.arange(1, m + 1)
    adj_sorted = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[order] = np.minimum(adj_sorted, 1.0)
    return out


def slice_tests(
    df: pd.DataFrame, outcome: str, by: list[str], alpha: float = 0.05, min_n: int = 5
) -> pd.DataFrame:
    """One-sided t-test (H1: mean > 0) per slice, with Holm and BH adjustments.

    Slices with fewer than ``min_n`` trades are reported but not tested.
    The number of tests is part of the output — always report it.
    """
    rows = []
    for key, g in df.groupby(by, sort=True):
        x = g[outcome].to_numpy(dtype=float)
        key = key if isinstance(key, tuple) else (key,)
        label = " / ".join(str(k) for k in key)
        if x.size < min_n or np.std(x, ddof=1) == 0:
            rows.append({"slice": label, "n": x.size, "mean": x.mean(), "t": np.nan, "p": np.nan})
            continue
        t, p = stats.ttest_1samp(x, 0.0, alternative="greater")
        rows.append({"slice": label, "n": x.size, "mean": x.mean(), "t": t, "p": p})
    res = pd.DataFrame(rows)
    tested = res["p"].notna()
    res["p_holm"] = np.nan
    res["p_bh"] = np.nan
    res.loc[tested, "p_holm"] = holm(res.loc[tested, "p"])
    res.loc[tested, "p_bh"] = benjamini_hochberg(res.loc[tested, "p"])
    res["significant_raw"] = res["p"] < alpha
    res["significant_holm"] = res["p_holm"] < alpha
    res["significant_bh"] = res["p_bh"] < alpha
    return res
