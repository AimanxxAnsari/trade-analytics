# Interview pack: trade-analytics

*Practise answering without notes. Everything here is backed by code and tests in the repo.*

## 30-second pitch
"I built a pipeline to answer the question a prop firm asks about a trader: is the edge real, and
how much should they be allowed to risk? I tested it on 422 real crypto perpetual trades that I
reconstructed from public exchange fills. The edge was statistically clear, with a Probabilistic
Sharpe Ratio above 0.999, but the record was heavily negatively skewed: a 94% win rate with a few
large losses that made up 98% of all losses. Full Kelly came out at 6.7x leverage, right next to the
7.1x level where one repeat of the worst trade wipes out the account. So the conclusion was: real
skill, but cap the size."

## 2-minute walkthrough
1. **Data:** public Hyperliquid fills (CC0). Rebuilt round trips: scale-ins, partial exits, a
   position flip split into two trades, and data gaps discarded rather than guessed. Validated by
   reconciling recomputed P&L against the exchange's figure (median error 4e-7).
2. **Edge:** iid and stationary bootstrap CIs on mean return, plus the Bayesian bootstrap; PSR and
   MinTRL because the outcomes are fat-tailed.
3. **Slices:** instrument by direction, corrected with Holm and BH; partial pooling showed slice
   differences were noise.
4. **Sizing:** Kelly with Bayesian-bootstrap uncertainty, and Monte Carlo drawdowns by leverage.
5. **Finding:** statistically significant, but tail risk dominates the sizing decision.

## Likely questions (with answers in short)
1. **Why the stationary bootstrap?** Streaks make iid resampling too optimistic; blocks keep
   short-range dependence. Here the CI widened only slightly, so dependence is mild.
2. **Why is "fraction of bootstrap means <= 0" not a p-value?** It is not computed under the
   null. You must centre the bootstrap distribution at zero first.
3. **What does PSR add over a t-test?** It accounts for skew and kurtosis; negative skew and fat
   tails reduce confidence. MinTRL rose from about 12 (normal) to 44 trades here.
4. **Why did profit factor drop from 9.8 to 2.2 in USD?** The big losses were on big positions.
   Per unit of size the trader is excellent; the sizing hurt.
5. **Why not bet full Kelly?** It is driven by the worst observed loss and by estimated
   parameters; out of sample the tail can be worse. Half Kelly keeps about 75% of growth in the textbook quadratic approximation (about 58% on this skewed record) with far
   smaller drawdowns.
6. **Holm vs BH?** Holm controls the chance of any false positive (FWER); BH controls the
   expected share of false positives (FDR) and is less conservative.
7. **How did you test the statistics?** Known answers: CI coverage near 95% on simulated data,
   the Kelly closed form f* = p - q/b, hand-computed Holm/BH, and wider block CIs on AR(1) data.
8. **What is the main weakness?** One account, one bull-market period, selected from a curated
   dataset; tail risk out of sample.
9. **How do you rebuild trades from fills?** Track running position per coin; open when flat; flip
   fills are split; continuity check on Start Position catches gaps.
10. **Why return on notional, not R?** No planned stops in the data; it's scale-free. USD is shown
    alongside to expose sizing effects.

11. **How do you handle journals in different formats?** A converter matches normalised
    column names against an alias table, lets explicit mappings override it, parses messy numbers
    and dates, derives missing fields (direction from signed size, P&L from prices, risk from stop
    or R column), and validates every row. It fails by default and writes a report of every
    decision, so nothing is silently guessed.
12. **Why report problems by file line?** So the person who owns the file can fix it directly;
    index numbers mean nothing to them.

## Must be able to rebuild from scratch
- [ ] Expectancy identity E = pW - qL (with scratches).
- [ ] iid bootstrap CI and null-imposed p-value (about 10 lines of NumPy).
- [ ] Stationary bootstrap index generation.
- [ ] PSR formula and why skew/kurtosis matter.
- [ ] Kelly binary derivation f* = p - q/b; numerical Kelly for general outcomes.
- [ ] Max drawdown of an equity path.
- [ ] Holm and BH adjustments.

## Numbers to remember
422 trades; 93.6% win rate; mean +0.83% per trade, CI [0.66%, 1.02%]; skew -1.9, kurtosis 35.8;
PSR > 0.999; MinTRL about 44; top-5 losses = 97.6% of USD losses; Kelly 6.7x vs 7.1x bound.

## STAR stories
- **Data validation:** *Situation:* fills, not trades. *Task:* trustworthy round trips.
  *Action:* reconstruction with continuity checks, then reconciled my P&L against the exchange's.
  *Result:* matched to 4e-7, and it also proved the exchange P&L excludes fees.
- **Overconfidence check:** *Situation:* huge statistical significance. *Task:* decide sizing.
  *Action:* Kelly with parameter uncertainty and wipe-out bound. *Result:* showed that
  significance and safe leverage are different questions.
