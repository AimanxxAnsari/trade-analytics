# trade-analytics

**Is there real skill in a discretionary trading record, and how much should be risked per trade?**

An independent quant research project that assesses a trading record the way a prop firm or fund
would assess a trader: expectancy, bootstrap and Bayesian inference on the edge, multiple-testing
control across slices, Probabilistic Sharpe Ratio, Monte Carlo drawdown and risk-of-ruin analysis,
and Kelly sizing under parameter uncertainty.

**Status:** in progress. The full pipeline runs end to end on a public **testing journal**
(422 BTC/ETH perpetual-futures trades reconstructed from public Hyperliquid fills). The same
pipeline will be run on a private personal journal.

## Headline results (testing journal)

| | |
|---|---|
| Trades / period | 422 / Mar 2024 - May 2025 |
| Win rate | 93.6% (payoff ratio 0.67 per unit notional; 0.15 in USD) |
| Mean return on notional | 0.83% per trade, 95% CI [0.66%, 1.02%] (stationary bootstrap) |
| Probabilistic Sharpe Ratio | > 0.999 (skew -1.9, kurtosis 35.8) |
| Loss concentration | 5 largest losses = 97.6% of all USD losses |
| Full Kelly leverage | 6.7x, against a 7.1x wipe-out bound set by the single worst trade |

The edge is statistically clear, but the record is a classic negatively skewed profile:
many small wins and a few large losses, concentrated in the largest positions. Full Kelly is
unusable here: it sits just below the leverage at which a repeat of the worst trade would wipe out
the account. Full report: [`reports/testing_journal/REPORT.md`](reports/testing_journal/REPORT.md).
Write-up: [`docs/projects/pillar-1/PROJECT.md`](docs/projects/pillar-1/PROJECT.md).

## Methods

| Module | Method | Status |
|---|---|---|
| `loaders.hyperliquid` | Fill-to-round-trip reconstruction (scale-in/out, flips, gap detection) | Done |
| `schema` | Canonical trade table and validation | Done |
| `metrics` | Win rate, payoff ratio, profit factor, expectancy | Done |
| `bootstrap` | iid and stationary block bootstrap (Efron 1979; Politis & Romano 1994) | Done |
| `sharpe` | Sharpe SE (Lo 2002), PSR and MinTRL (Bailey & López de Prado 2012) | Done |
| `bayes` | Beta-Binomial win rate, Bayesian bootstrap (Rubin 1981), partial pooling | Done |
| `multiple_testing` | Holm (1979), Benjamini-Hochberg (1995), slice tests | Done |
| `monte_carlo` | Trade-sequence resampling: drawdown distribution, risk of ruin | Done |
| `sizing` | Kelly with Bayesian-bootstrap parameter uncertainty | Done |
| `synthetic` | Generators with known answers for tests | Done |
| `report` | End-to-end report with figures | Done |

Every statistical method is tested against a known answer first (hand calculations, closed forms,
or synthetic data with a known true value). 39 tests.

## Data

- **Testing journal** (`data/testing_journal/`): derived from the public Kaggle dataset
  "Historical Trade Data" (Hyperliquid fills, CC0 1.0). See its
  [README](data/testing_journal/README.md) and [ADR-0004](docs/decisions/ADR-0004-testing-journal.md).
- **Personal journal**: never committed ([ADR-0001](docs/decisions/ADR-0001-private-trade-data.md)).

## Run

```bash
uv sync --all-groups
uv run pytest
uv run python scripts/run_report.py      # writes reports/testing_journal/
```

To rebuild the testing journal from the raw Kaggle file:

```bash
uv run python scripts/build_testing_journal.py path/to/historical_data.csv
```

## Documentation

- [Project write-up](docs/projects/pillar-1/PROJECT.md)
- [Design docs](docs/design/)
- [Decision records](docs/decisions/)
- [Development log](docs/devlog/)
- [Learning notes](docs/learning/)
- [References](references.bib)
