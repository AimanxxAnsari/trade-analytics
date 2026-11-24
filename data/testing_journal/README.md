# Testing journal

A public, reproducible stand-in for a personal trading journal, used to build and test the
analysis pipeline.

| | |
|---|---|
| File | `testing_journal.csv` (422 trades) |
| Source | Kaggle, "Historical Trade Data" by pradeepjswl: fills from the Hyperliquid perpetual-futures exchange |
| Source licence | CC0 1.0 Universal (public domain) |
| Source file SHA-256 | recorded in `provenance.json` |
| Account | one wallet address from the dataset (in `provenance.json`); selection rule in ADR-0004 |
| Instruments | BTC and ETH perpetual futures |
| Period (UTC) | 2024-03-13 to 2025-05-01 |
| Built by | `scripts/build_testing_journal.py` |

## Columns

Canonical schema (`docs/design/trade-schema.md`) plus:

| Column | Meaning |
|---|---|
| `fees` | total fees across all fills of the trade (USD) |
| `pnl` | sum of the exchange's `Closed PnL` minus fees (USD) |
| `price_pnl` | P&L recomputed from entry/exit VWAPs (gross); reconciles with `Closed PnL` |
| `notional` | entry VWAP x size (USD) |
| `max_position` | largest position held during the trade |
| `n_fills` | number of fills in the round trip |
| `liquidated` | any liquidation fill in the trade |

## Caveats

- Not a personal journal: no planned stop, so no R-multiples. Outcomes are measured as return on
  notional (ADR-0005).
- Timestamps have minute resolution (source granularity).
- Two trades interrupted by data gaps were discarded rather than guessed.
