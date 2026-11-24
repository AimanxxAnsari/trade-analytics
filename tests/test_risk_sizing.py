"""Known-answer tests for Monte Carlo drawdowns and Kelly sizing."""

import numpy as np
import pytest

from trade_analytics.monte_carlo import drawdown_risk, max_drawdown, simulate_equity
from trade_analytics.sizing import growth_rate, kelly_fraction, kelly_with_uncertainty


def test_max_drawdown_hand_computed():
    path = np.array([[1.0, 1.2, 0.9, 1.5, 1.2]])
    # peak 1.2 -> 0.9 is -25%; peak 1.5 -> 1.2 is -20%
    assert max_drawdown(path)[0] == pytest.approx(0.25)


def test_constant_positive_outcomes_never_draw_down():
    paths = simulate_equity(np.full(50, 0.1), fraction=0.5, n_paths=10)
    assert np.allclose(max_drawdown(paths), 0.0)
    assert paths[0, -1] == pytest.approx(1.05**50)


def test_wipeout_when_fraction_times_loss_reaches_minus_one():
    paths = simulate_equity(np.array([-1.0]), fraction=1.0, n_paths=5, n_trades=3)
    assert np.all(paths[:, -1] == 0.0)


def test_bigger_size_means_bigger_drawdowns():
    x = np.random.default_rng(0).normal(0.05, 1.0, 300)
    t = drawdown_risk(x, fractions=[0.01, 0.05, 0.1], n_paths=2000).table
    assert t["median_max_dd"].is_monotonic_increasing
    assert t["p_ruin"].is_monotonic_increasing


def test_kelly_binary_closed_form():
    # 60 wins of +1R and 40 losses of -1R: f* = p - q/b = 0.6 - 0.4 = 0.2
    x = np.array([1.0] * 60 + [-1.0] * 40)
    assert kelly_fraction(x) == pytest.approx(0.2, abs=1e-5)


def test_kelly_asymmetric_payoff():
    # p = 0.5, b = 2: f* = 0.5 - 0.5/2 = 0.25
    x = np.array([2.0] * 50 + [-1.0] * 50)
    assert kelly_fraction(x) == pytest.approx(0.25, abs=1e-5)


def test_kelly_zero_without_edge_and_growth_negative_when_overbetting():
    x = np.array([1.0] * 50 + [-1.0] * 50)
    assert kelly_fraction(x) == 0.0
    edge = np.array([1.0] * 60 + [-1.0] * 40)
    assert growth_rate(edge, 0.2) > 0 > growth_rate(edge, 0.5)
    assert growth_rate(edge, 1.0) == -np.inf


def test_kelly_uncertainty_spread():
    x = np.array([1.0] * 60 + [-1.0] * 40)
    k = kelly_with_uncertainty(x, n_draws=400)
    assert k.point == pytest.approx(0.2, abs=1e-5)
    assert k.quantile(0.05) < 0.2 < k.quantile(0.95)
