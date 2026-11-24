# Design: canonical trade table

**Status:** accepted · 2026-11-24

## Purpose
One validated table that every analysis consumes, so that statistics never depend on the quirks of
a particular broker or journal export.

## Scope / non-goals
- In scope: closed trades with realised P&L.
- Out of scope (for now): open positions, intra-trade price paths (MAE/MFE), multi-leg trades.

## Schema
| Column | Type | Required | Rule |
|---|---|---|---|
| `trade_id` | str | yes | unique |
| `instrument` | str | yes | free text, normalised by loader |
| `direction` | str | yes | `long` or `short` |
| `entry_time`, `exit_time` | datetime, tz-aware UTC | yes | exit ≥ entry |
| `entry_price`, `exit_price` | float | yes | > 0 |
| `size` | float | yes | > 0 |
| `pnl` | float | yes | net of fees, account currency, no NaN |
| `risk_amount` | float | — | > 0; required for R-multiples |
| `stop_price`, `fees`, `setup` | — | — | optional |

## Interfaces
- `validate_trades(df) -> df` — returns the same object if valid; raises `TradeSchemaError`
  listing **all** problems found.
- `r_multiples(df) -> Series` — `pnl / risk_amount`.

## Invariants & edge cases
- Validation reports every problem at once (faster fixing of a messy export).
- Naive timestamps are rejected: mixing time zones silently would corrupt session analysis.
- Time-order check only runs when both time columns are valid datetimes.
- `pnl` is **net**; if the export gives gross P&L and fees separately, the loader nets them.

## Test plan
- One valid synthetic table passes unchanged.
- One mutation per rule fails with the right message (parametrised).
- Multiple simultaneous violations are all reported.

## Open questions
- Does the journal record `risk_amount` or only `stop_price`? If only the stop:
  `risk_amount = |entry − stop| × size × contract multiplier` (needs an instrument table).
- Account currency vs instrument currency for FX and gold P&L.
