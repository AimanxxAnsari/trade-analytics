# trade-analytics

**Is there real skill in a discretionary trading record — and how much should be risked per trade?**

An independent quant research project analysing a personal record of ~300 discretionary trades
(equity index, crude oil, gold and FX) with the tools a prop firm or fund would use to assess a
trader: expectancy in R-multiples, bootstrap and Bayesian inference on the edge, multiple-testing
control, Monte Carlo drawdown and risk-of-ruin analysis, and Kelly-based position sizing under
parameter uncertainty.

> **Status:** 🚧 in progress — data schema, validation and descriptive metrics done; inference
> modules next. See [`docs/devlog/`](docs/devlog/).

## Research questions

1. Is the expectancy of the trade sequence distinguishable from zero, after accounting for sample
   size, fat tails and serial dependence?
2. What is the posterior probability that the edge is positive, and how many trades are needed
   before it is credible?
3. Which breakdowns (instrument, direction, setup) survive multiple-testing correction?
4. What drawdowns and risk of ruin does the record imply at different risk-per-trade levels?
5. What fraction of Kelly is justified once parameter uncertainty is included?

## Methods (planned → done)

| Module | Method | Status |
|---|---|---|
| `schema` | Canonical trade table + validation | ✅ |
| `metrics` | Win rate, payoff ratio, profit factor, expectancy (R-multiples) | ✅ |
| `bootstrap` | iid and stationary block bootstrap CIs (Efron 1979; Politis & Romano 1994) | ⏳ |
| `sharpe` | Sharpe SE (Lo 2002), Probabilistic Sharpe Ratio & MinTRL (Bailey & López de Prado 2012) | ⏳ |
| `bayes` | Beta-Binomial win rate; hierarchical pooling across instruments | ⏳ |
| `multiple_testing` | Holm (1979), Benjamini–Hochberg (1995) | ⏳ |
| `monte_carlo` | Trade-sequence resampling: drawdown distribution, risk of ruin | ⏳ |
| `sizing` | Kelly / fractional Kelly with posterior parameter uncertainty | ⏳ |

## Privacy

The raw trade record is **never committed** — only code, tests on synthetic data, and aggregated
results/charts. See [ADR-0001](docs/decisions/ADR-0001-private-trade-data.md).

## Run

```bash
uv sync --all-groups
uv run pytest
```

## Documentation

- [Project write-up](docs/projects/pillar-1/PROJECT.md)
- [Design: trade schema](docs/design/trade-schema.md)
- [Decision records](docs/decisions/)
- [Development log](docs/devlog/)
- [References](references.bib)
