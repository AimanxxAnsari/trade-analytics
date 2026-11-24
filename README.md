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

| Module | Method |
|---|---|
| `ingest`, `cli` | Check and convert journals in any format to the canonical schema; `trade-journal` command |
| `loaders.hyperliquid` | Fill-to-round-trip reconstruction (scale-in/out, flips, gap detection) |
| `schema` | Canonical trade table and validation |
| `metrics` | Win rate, payoff ratio, profit factor, expectancy |
| `bootstrap` | iid and stationary block bootstrap (Efron 1979; Politis & Romano 1994) |
| `sharpe` | Sharpe SE (Lo 2002), PSR and MinTRL (Bailey & López de Prado 2012) |
| `bayes` | Beta-Binomial win rate, Bayesian bootstrap (Rubin 1981), partial pooling |
| `multiple_testing` | Holm (1979), Benjamini-Hochberg (1995), slice tests |
| `monte_carlo` | Trade-sequence resampling: drawdown distribution, risk of ruin |
| `sizing` | Kelly with Bayesian-bootstrap parameter uncertainty |
| `synthetic` | Generators with known answers for tests |
| `report` | End-to-end report with figures |

Every statistical method is tested against a known answer first (hand calculations, closed forms,
or synthetic data with a known true value). 52 tests.

## Data

- **Testing journal** (`data/testing_journal/`): derived from the public Kaggle dataset
  "Historical Trade Data" (Hyperliquid fills, CC0 1.0). See its
  [README](data/testing_journal/README.md) and [ADR-0004](docs/decisions/ADR-0004-testing-journal.md).
- **Personal journal**: never committed ([ADR-0001](docs/decisions/ADR-0001-private-trade-data.md)).

## Use your own journal

Any CSV journal can be checked, converted to the canonical schema and analysed:

```bash
uv run trade-journal check   my_journal.csv                    # is it already canonical?
uv run trade-journal convert my_journal.csv -o data/clean/journal.csv --dayfirst
uv run trade-journal analyse my_journal.csv -o reports/private/my_journal
```

Column names are matched automatically (e.g. `Symbol`, `Side`, `Open Time`, `P&L`, `Commission`).
Numbers like `$1,250.00` and `(320.50)`, day-first dates, signed sizes, gross P&L with costs,
R-multiple columns and stop prices are handled. Every mapping and derivation is written to a
conversion report, and invalid rows are listed by file line. For unusual files, generate a
mapping template, edit it, and pass it back:

```bash
uv run trade-journal convert my_journal.csv --write-mapping mapping.json
uv run trade-journal convert my_journal.csv --mapping mapping.json -o data/clean/journal.csv
```

Presets: `--preset mt4` (MetaTrader 4/5 history export). Examples:
[`examples/alien_journals/`](examples/alien_journals/). Design:
[`docs/design/journal-ingest.md`](docs/design/journal-ingest.md).
Outputs written under `data/`, `out/` and `reports/private/` are git-ignored.

## Run

```bash
uv sync --all-groups
uv run pytest
uv run python scripts/run_report.py      # writes reports/testing_journal/
uv run trade-journal --help
```

To rebuild the testing journal from the raw Kaggle file:

```bash
uv run python scripts/build_testing_journal.py path/to/historical_data.csv
```

## Notebook

[`notebooks/pillar1_walkthrough.ipynb`](notebooks/pillar1_walkthrough.ipynb): the whole pipeline step by step on the
testing journal, with the reasoning behind each method and known-answer sanity checks. It is
executed by the test suite, so it always runs.

## Documentation

- [Project write-up](docs/projects/pillar-1/PROJECT.md)
- [Design docs](docs/design/)
- [Decision records](docs/decisions/)
- [Development log](docs/devlog/)
- [Learning notes](docs/learning/)
- [References](references.bib)
