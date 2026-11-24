# ADR-0004: Public testing journal from Hyperliquid fills

- **Date:** 2026-11-24
- **Status:** accepted

## Context
The analysis pipeline needs a realistic trade record that can be committed, shown publicly and
used in CI. The personal journal must stay private (ADR-0001), and purely synthetic trades lack
the messiness of real data (scale-ins, flips, gaps, fat tails).

## Options considered
1. **Synthetic trades only.** Fully controlled, but not realistic; results are uninteresting.
2. **Kaggle "trading journal" templates or simulated journals.** Few exist with real outcomes,
   and licences are often unclear.
3. **Real exchange fills with a permissive licence, reconstructed into round trips.** Realistic
   and legally reusable, but needs a reconstruction step.

## Decision
Option 3, using the Kaggle dataset "Historical Trade Data" (Hyperliquid fills, **CC0 1.0**).
The ~47 MB source file is not committed; the derived 422-trade journal and its provenance
(source SHA-256, account, diagnostics) are.

**Account selection rule** (decided before looking at performance): among the dataset's 32
accounts, the one whose perpetual-futures fills reconstruct into the most round trips with the
fewest continuity gaps and flips, trading a small number of liquid instruments. Result: one
account trading BTC and ETH, 422 trades, 2 gaps, 1 flip.

## Consequences
- The pipeline is demonstrated on real, public data; anyone can re-derive the journal.
- Selection bias: the dataset's creator chose which accounts to include, and accounts active on a
  single exchange over one period are not a random sample of traders. Results describe this
  account, not traders in general.
- The `.gitignore` gains a narrow exception for `data/testing_journal/`.
