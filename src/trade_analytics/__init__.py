"""trade_analytics — statistical analysis of a discretionary trading record."""

from trade_analytics.metrics import (
    PerformanceSummary,
    expectancy,
    payoff_ratio,
    profit_factor,
    r_multiples,
    summarise,
    win_rate,
)
from trade_analytics.schema import REQUIRED_COLUMNS, TradeSchemaError, validate_trades

__all__ = [
    "REQUIRED_COLUMNS",
    "PerformanceSummary",
    "TradeSchemaError",
    "expectancy",
    "payoff_ratio",
    "profit_factor",
    "r_multiples",
    "summarise",
    "validate_trades",
    "win_rate",
]
