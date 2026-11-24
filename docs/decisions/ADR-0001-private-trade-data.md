# ADR-0001: Raw trade data stays private

- **Date:** 2026-11-24
- **Status:** accepted

## Context
The project analyses a personal trading record. The repository is intended to be shown publicly as
a portfolio piece. The raw record contains personal financial information.

## Options considered
1. **Commit the raw data** — fully reproducible by anyone; exposes personal financial data. ❌
2. **Commit an anonymised version** (shifted dates, scaled P&L) — partially reproducible; risk of
   re-identification and of results that don't match the real analysis. ❌
3. **Keep raw data local; commit code, synthetic-data tests and aggregated results only.** ✅

## Decision
Option 3. `data/*` and all spreadsheet/CSV/parquet files are git-ignored; tests use synthetic
trades only; published outputs are aggregate statistics and charts.

## Consequences
- Others can run the code and tests but cannot reproduce the exact numbers.
- A synthetic-trade generator is needed for demos and tests.
- Every commit must be checked for accidental data files (`.gitignore` + review).
