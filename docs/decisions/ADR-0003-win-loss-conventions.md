# ADR-0003: Win / loss / scratch conventions

- **Date:** 2026-11-24
- **Status:** accepted

## Context
Descriptive statistics depend on how zero-P&L ("scratch") trades are treated. Different platforms
use different conventions, which silently changes win rate and expectancy.

## Options considered
1. Count scratches as losses — overstates losing frequency.
2. Drop scratches entirely — inflates win rate and hides that capital was at risk.
3. **Keep scratches as a separate category:** in the denominator of win rate and in expectancy,
   excluded from average win / average loss. ✅

## Decision
Option 3. Win = outcome > 0, loss = outcome < 0, scratch = outcome == 0.

## Consequences
- `expectancy == p·avg_win − q·|avg_loss|` holds exactly with p, q as rates over **all** trades —
  verified by a Hypothesis property test.
- Win rate is comparable across samples with different scratch frequencies only if the scratch
  count is also reported (it is, in `PerformanceSummary`).
