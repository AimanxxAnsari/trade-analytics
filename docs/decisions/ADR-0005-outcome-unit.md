# ADR-0005: Outcome unit when no planned stop exists

- **Date:** 2026-11-24
- **Status:** accepted

## Context
R-multiples (P&L / planned risk) are the preferred unit, but the testing journal has no planned
stop. Raw USD P&L is dominated by position size: one large trade can outweigh hundreds of small
ones, so USD statistics mix *skill* with *sizing decisions*.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| USD P&L | what the account actually earned | size-dependent; not comparable across trades |
| Return on margin | reflects leverage used | margin not in the data |
| **Return on notional** (pnl / (entry price x size)) | scale-free; available; comparable across BTC and ETH | ignores leverage; not risk-normalised like R |
| Volatility-normalised return | closest to R | needs market data; adds a model |

## Decision
- Use **R-multiples** when `risk_amount` is present (personal journal).
- Otherwise use **return on notional**. Report USD statistics alongside, because the gap between
  the two is itself informative (it reveals how sizing affected results).
- Monte Carlo and Kelly then size in **leverage** (notional / equity) instead of fraction risked.

## Consequences
- Statistics on the testing journal describe trade selection and timing; sizing effects appear in
  the USD columns and in the size-quartile analysis.
- Volatility normalisation is a possible later extension.
