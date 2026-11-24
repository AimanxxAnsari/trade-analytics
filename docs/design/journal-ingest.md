# Design: checking and converting journals in any format

**Status:** accepted · 2026-11-24 · Modules: `trade_analytics.ingest`, `trade_analytics.cli`

## Purpose
Real journals arrive in many shapes: broker exports (MetaTrader), spreadsheets, journaling apps.
The analysis only accepts the canonical schema ([trade-schema.md](trade-schema.md)). This
component checks a file and, if needed, converts it, recording every decision it made.

## Interface
```
trade-journal check   FILE                       # exit 0 if canonical, 1 otherwise (+ mapping guess)
trade-journal convert FILE -o OUT [options]      # writes OUT and OUT.conversion.md
trade-journal analyse FILE -o DIR [options]      # convert if needed, then the full report
```
Options: `--preset mt4`, `--mapping file.json`, `--write-mapping file.json`, `--tz`,
`--dayfirst`, `--time-format`, `--multiplier`, `--pnl-gross`, `--drop-invalid`.

Python: `convert_journal(raw_df, ConversionOptions(...)) -> ConversionResult` with `.trades`,
`.mapping`, `.notes`, `.row_issues`, `.to_markdown()`.

## Pipeline
1. **Column mapping.** Explicit mapping (preset or JSON) wins. Remaining canonical fields are
   matched against an alias table on *normalised* headers (lower case, punctuation to spaces:
   `P&L` -> `p l`, `S / L` -> `s l`). Each source column is used at most once; aliases are tried
   in priority order (e.g. `pnl` before `profit`).
2. **Value parsing.**
   - Numbers: currency symbols and thousands separators removed; `(320.50)` -> -320.5; unicode minus.
   - Directions: first word of the value; `buy/long/b/l/1` -> long, `sell/short/s/-1` -> short.
   - Times: explicit format or mixed inference; `--dayfirst`; naive times localised to `--tz`
     and converted to UTC.
3. **Derivations** (each recorded in the report).
   | Missing field | Derived from |
   |---|---|
   | direction | sign of size |
   | exit_time | entry_time (date-only journals) |
   | pnl | sign x (exit - entry) x size x multiplier - fees |
   | net pnl | gross pnl - fees (`--pnl-gross`) |
   | risk_amount | \|pnl / R\| if an R column exists, else \|entry - stop\| x size x multiplier |
   | trade_id | generated `J00001...` |
   | notional | entry x size x multiplier (fallback outcome unit, ADR-0005) |
4. **Costs.** All cost-like columns (commission, swap, taxes, fees, funding...) are summed. If any
   value is negative the columns are treated as signed cash flows (MetaTrader convention:
   commission -7.00), so fee = -sum; otherwise as positive costs.
5. **Row validation.** Each row checked for: recognised direction, parseable times, positive
   prices and size, P&L present, instrument present, exit >= entry, unique id. Problems are
   reported by **file line** (header = line 1). Default: fail. `--drop-invalid`: drop and list.
6. **Table validation.** The result must pass `validate_trades`.

## Invariants
- No silent changes: every mapping, derivation, convention and dropped row is in the report.
- A canonical journal converts to itself (round-trip test on the testing journal).
- Conversion outputs of personal journals go to git-ignored folders (`data/`, `out/`,
  `reports/private/`).

## Known limitations
- One contract multiplier per file. Journals mixing instruments with different multipliers
  should provide P&L and risk columns directly, or be converted per instrument.
- Multi-leg trades and partial fills must already be aggregated into round trips (or use a
  dedicated loader such as `loaders.hyperliquid`).
- The alias table is heuristic. `check` prints the guess and `--write-mapping` lets the user
  correct it explicitly.

## Test plan
`tests/test_ingest.py`: header normalisation; number and direction parsing; alias mapping with
explicit override; MT4 preset (gross P&L, signed fees, risk from stop, non-trade row dropped);
generic journal (day-first dates, money formats, R column, generated ids); signed size and
price-derived P&L with time-zone conversion; actionable error for missing fields; canonical
round trip; CLI check/convert and mapping-template round trip.
