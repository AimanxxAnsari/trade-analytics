"""Known-answer tests for the inference modules (bootstrap, Sharpe, Bayes, multiple testing)."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from trade_analytics.bayes import (
    bayesian_bootstrap_mean,
    breakeven_win_rate,
    partial_pool_win_rates,
    win_rate_posterior,
)
from trade_analytics.bootstrap import bootstrap_mean, stationary_indices
from trade_analytics.multiple_testing import benjamini_hochberg, holm, slice_tests
from trade_analytics.sharpe import (
    min_track_record_length,
    probabilistic_sharpe_ratio,
    sharpe_ratio,
    sharpe_se_iid,
)
from trade_analytics.synthetic import binary_outcomes

# ---------------------------------------------------------------- bootstrap


def test_bootstrap_ci_coverage_close_to_nominal():
    """95% CI should contain the true mean in roughly 95% of repeated samples."""
    true_mean, hits, reps = 0.2, 0, 300
    for s in range(reps):
        x = np.random.default_rng(1000 + s).normal(true_mean, 1.0, 200)
        r = bootstrap_mean(x, n_boot=600, seed=s)
        hits += r.ci_low <= true_mean <= r.ci_high
    assert 0.90 <= hits / reps <= 0.99


def test_bootstrap_p_value_behaviour():
    rng = np.random.default_rng(0)
    strong = bootstrap_mean(rng.normal(0.5, 1, 300), n_boot=2000)
    none = bootstrap_mean(rng.normal(-0.2, 1, 300), n_boot=2000)
    assert strong.p_value < 0.01
    assert none.p_value > 0.5


def test_stationary_indices_valid_and_blocky():
    rng = np.random.default_rng(0)
    idx = stationary_indices(100, 50, block_length=10, rng=rng)
    assert idx.shape == (50, 100)
    assert idx.min() >= 0 and idx.max() < 100
    # With L = 10, about 90% of steps continue the current block.
    cont = np.mean((idx[:, 1:] - idx[:, :-1]) % 100 == 1)
    assert 0.85 < cont < 0.95


def test_stationary_bootstrap_wider_under_autocorrelation():
    """With positively autocorrelated outcomes, block resampling must widen the CI."""
    rng = np.random.default_rng(3)
    e = rng.normal(0, 1, 600)
    x = np.empty_like(e)
    x[0] = e[0]
    for t in range(1, x.size):
        x[t] = 0.7 * x[t - 1] + e[t]
    iid = bootstrap_mean(x, n_boot=2000, method="iid")
    blk = bootstrap_mean(x, n_boot=2000, method="stationary", block_length=20)
    assert (blk.ci_high - blk.ci_low) > 1.5 * (iid.ci_high - iid.ci_low)


# ---------------------------------------------------------------- Sharpe


def test_sharpe_se_formula():
    assert sharpe_se_iid(0.0, 100) == pytest.approx(0.1)
    assert sharpe_se_iid(1.0, 150) == pytest.approx(np.sqrt(1.5 / 150))


def test_psr_matches_normal_formula_for_gaussian_data():
    x = np.random.default_rng(0).normal(0.1, 1.0, 5000)
    sr = sharpe_ratio(x)
    g3 = stats.skew(x, bias=False)
    g4 = stats.kurtosis(x, fisher=False, bias=False)
    expected = stats.norm.cdf(
        sr * np.sqrt(x.size - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr**2)
    )
    assert probabilistic_sharpe_ratio(x) == pytest.approx(expected)


def test_min_trl_infinite_without_edge_and_finite_with():
    assert min_track_record_length(np.random.default_rng(0).normal(-0.1, 1, 500)) == np.inf
    trl = min_track_record_length(np.random.default_rng(0).normal(0.3, 1, 500))
    # Normal approx: 1 + (1 + SR^2/2) (1.645/SR)^2 ~= 31 for SR = 0.3
    assert 15 < trl < 60


# ---------------------------------------------------------------- Bayes


def test_beta_posterior_parameters_and_tail():
    post = win_rate_posterior(wins=60, n=100)
    assert (post.alpha, post.beta) == (61, 41)
    assert post.mean == pytest.approx(61 / 102)
    assert post.prob_above(0.5) == pytest.approx(stats.beta.sf(0.5, 61, 41))


def test_breakeven_win_rate():
    assert breakeven_win_rate(1.0) == pytest.approx(0.5)
    assert breakeven_win_rate(2.0) == pytest.approx(1 / 3)


def test_bayesian_bootstrap_centres_on_sample_mean():
    x = binary_outcomes(400, 0.55, 1.0, seed=1)
    draws = bayesian_bootstrap_mean(x, n_draws=5000)
    assert draws.mean() == pytest.approx(x.mean(), abs=0.01)
    assert draws.std() == pytest.approx(x.std() / np.sqrt(x.size), rel=0.1)


def test_partial_pooling_shrinks_small_groups_most():
    res = partial_pool_win_rates(["big", "small", "mid"], wins=[300, 9, 55], n=[500, 10, 100])
    # The 10-trade group at 90% should be pulled strongly toward the overall ~60%.
    assert res.pooled[1] < res.raw[1]
    shrink = np.abs(res.pooled - res.raw)
    assert shrink[1] > shrink[2] > shrink[0]


# ---------------------------------------------------------------- multiple testing

P = [0.01, 0.04, 0.03, 0.005]


def test_holm_hand_computed():
    # sorted p .005 .01 .03 .04 x (4,3,2,1) = .02 .03 .06 .04 -> running max .02 .03 .06 .06
    assert holm(P) == pytest.approx([0.03, 0.06, 0.06, 0.02])


def test_bh_hand_computed():
    # sorted p x m/k = .02 .02 .04 .04 -> running min from the top keeps them
    assert benjamini_hochberg(P) == pytest.approx([0.02, 0.04, 0.04, 0.02])


def test_slice_tests_reports_every_slice():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "g": np.repeat(["a", "b", "c"], [50, 50, 3]),
            "x": np.concatenate([rng.normal(1, 1, 50), rng.normal(0, 1, 50), [1, 2, 3]]),
        }
    )
    res = slice_tests(df, "x", ["g"])
    assert list(res["slice"]) == ["a", "b", "c"]
    assert np.isnan(res.loc[2, "p"])  # too small to test
    assert bool(res.loc[0, "significant_holm"])
