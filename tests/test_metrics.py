import math

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from trade_analytics import (
    expectancy,
    payoff_ratio,
    profit_factor,
    r_multiples,
    summarise,
    win_rate,
)

# Hand-computed reference: R = [2, -1, -1, 3, -1]
#   wins = [2, 3]        -> avg win 2.5, gross profit 5
#   losses = [-1,-1,-1]  -> avg loss -1, gross loss 3
#   win rate 2/5 = 0.4; payoff 2.5; profit factor 5/3; expectancy 2/5 = 0.4
#   check: p*W - q*L = 0.4*2.5 - 0.6*1 = 0.4
R = [2.0, -1.0, -1.0, 3.0, -1.0]


def test_hand_computed_values():
    assert win_rate(R) == pytest.approx(0.4)
    assert payoff_ratio(R) == pytest.approx(2.5)
    assert profit_factor(R) == pytest.approx(5 / 3)
    assert expectancy(R) == pytest.approx(0.4)


def test_summary_counts_and_scratches():
    s = summarise([1.0, 0.0, -1.0, 0.0])
    assert (s.n_trades, s.n_wins, s.n_losses, s.n_scratches) == (4, 1, 1, 2)
    assert s.win_rate == pytest.approx(0.25)  # scratches stay in the denominator
    assert s.expectancy == pytest.approx(0.0)


def test_edge_cases():
    assert math.isinf(profit_factor([1.0, 2.0]))
    assert math.isnan(payoff_ratio([1.0, 2.0]))
    assert math.isnan(profit_factor([0.0, 0.0]))
    with pytest.raises(ValueError):
        expectancy([])
    with pytest.raises(ValueError):
        expectancy([1.0, float("nan")])


@given(st.lists(st.floats(-50, 50, allow_nan=False), min_size=1, max_size=200))
def test_expectancy_identity(outcomes):
    """mean(x) == p*avg_win - q*|avg_loss| with rates over ALL trades."""
    x = np.asarray(outcomes)
    n = x.size
    wins, losses = x[x > 0], x[x < 0]
    p, q = wins.size / n, losses.size / n
    avg_w = wins.mean() if wins.size else 0.0
    avg_l = abs(losses.mean()) if losses.size else 0.0
    assert expectancy(x) == pytest.approx(p * avg_w - q * avg_l, abs=1e-9)


def test_r_multiples():
    trades = pd.DataFrame({"pnl": [200.0, -100.0], "risk_amount": [100.0, 100.0]})
    assert r_multiples(trades).tolist() == [2.0, -1.0]
    with pytest.raises(ValueError):
        r_multiples(pd.DataFrame({"pnl": [1.0]}))
