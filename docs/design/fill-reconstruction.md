# Design: reconstructing round-trip trades from exchange fills

**Status:** accepted · 2026-11-24 · Module: `trade_analytics.loaders.hyperliquid`

## Purpose
Exchanges report **fills** (each partial execution). Trade analysis needs **round trips**: from flat,
into a position (possibly over several fills), and back to flat.

## Input
Hyperliquid fills: account, coin, execution price, size, side, IST timestamp (minute resolution),
`Start Position` (position before the fill), direction label, `Closed PnL`, fee.

## Algorithm (per account and coin, in time order; ties broken by source row order)
1. `end = start + side * qty`.
2. **Continuity check:** if `start` differs from the previous fill's `end`, the data has a gap:
   discard any open trade.
3. **Opening:** with no open trade, a fill starting flat opens one in the direction of `end`.
   Fills starting non-flat are skipped until the position is flat again.
4. **Entry fills** (same side as the trade) add to entry quantity and notional.
5. **Exit fills** reduce the position; `Closed PnL` is accumulated.
6. **Flip** (sells more than the long position, or vice versa): split the fill. The closing part
   ends the old trade; the remainder opens a new trade at the same price and time. Fees are split
   pro rata by quantity.
7. The trade closes when the position returns to flat (tolerance: 1e-9 + 1e-6 x scale).

## Output per trade
Entry/exit VWAP, size, direction, entry/exit times, `pnl = sum(Closed PnL) - sum(fees)`,
`price_pnl = sign x (exit VWAP - entry VWAP) x size`, notional, fills, liquidation flag.

## Invariants and validation
- Total entry quantity equals total exit quantity for every completed trade.
- `price_pnl` must reconcile with the exchange's `Closed PnL`. On the testing journal the median
  relative difference is 4e-7, which confirms both the reconstruction and that `Closed PnL` is
  gross of fees.
- Output passes `validate_trades`.

## Edge cases
| Case | Handling |
|---|---|
| Position open when data starts | skipped until flat (counted in diagnostics) |
| Gap mid-trade | trade discarded (counted), not guessed |
| Same-minute fills | original row order |
| Spot fills (`@n`, `X/Y`) | excluded |
| Liquidation / auto-deleveraging fills | treated as exits; trade flagged |

## Test plan
Hand-built fill sequences: scale-in/scale-out VWAPs and net P&L; a flip split into two trades with
pro-rata fees; a gap that discards a trade and skips until flat.
