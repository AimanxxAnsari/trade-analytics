# Skill or luck? A statistical assessment of a trading record

*Working paper. Results below are for the public testing journal; the personal journal will be
analysed with the same pipeline.*

## Abstract
We assess a record of 422 BTC and ETH perpetual-futures trades (March 2024 to May 2025),
reconstructed from public Hyperliquid exchange fills, with the tools a prop firm would use to judge
a trader. The mean return on notional is 0.83% per trade (95% stationary-bootstrap CI 0.66% to
1.02%; Probabilistic Sharpe Ratio > 0.999), and every instrument/direction slice survives Holm
correction. The edge is statistically clear but comes from a strongly negatively skewed profile:
a 93.6% win rate with small wins and rare large losses (skew -1.9, kurtosis 35.8). The five largest
losses make up 97.6% of all USD losses and fell on large positions. Growth-optimal (Kelly) leverage
of 6.7x sits just below the 7.1x leverage at which a repeat of the single worst trade would wipe out
the account. A statistically significant edge does not imply that aggressive sizing is safe.

## 1. Introduction
Prop-trading firms, multi-manager funds and allocators must decide from a short track record
whether a trader has an edge and how much capital to give them. With a few hundred trades,
fat-tailed outcomes and many ways to slice the record, luck is easily mistaken for skill. This
project builds a reusable, tested pipeline for that assessment.

**Who uses this in industry:** prop firms and funded-trader programmes (capital allocation,
drawdown limits), multi-manager hedge funds (manager evaluation), risk teams (position-size caps).

## 2. Related work
- Expectancy and R-multiples as the unit of trade analysis (Tharp).
- Sampling error of the Sharpe ratio (Lo 2002); Probabilistic Sharpe Ratio and Minimum Track Record
  Length (Bailey & López de Prado 2012).
- Bootstrap inference (Efron 1979); stationary bootstrap for dependent data (Politis & Romano 1994);
  Bayesian bootstrap (Rubin 1981).
- Multiple-testing control (Holm 1979; Benjamini & Hochberg 1995).
- Growth-optimal sizing (Kelly 1956; Thorp 2006) and fractional Kelly under uncertainty
  (MacLean, Thorp & Ziemba 2011).
- Evidence on retail and day-trader skill (Barber & Odean 2000; Barber, Lee, Liu & Odean 2014).

## 3. Data
- **Source:** Kaggle "Historical Trade Data" (Hyperliquid fills, CC0), 211,224 fills from
  32 accounts. One account selected by data quality before looking at performance
  ([ADR-0004](../../decisions/ADR-0004-testing-journal.md)).
- **Reconstruction:** 7,562 perpetual-futures fills turned into 422 round trips; 2 trades
  discarded at data gaps; 1 position flip split
  ([design](../../design/fill-reconstruction.md)). The P&L recomputed from prices matches the
  exchange's reported P&L (median relative difference 4e-7).
- **Composition:** BTC long 240, BTC short 97, ETH long 60, ETH short 25. Median holding time
  4.6 hours.
- **Outcome unit:** return on notional, because there is no planned stop
  ([ADR-0005](../../decisions/ADR-0005-outcome-unit.md)). USD figures reported alongside.

## 4. Method
| Question | Method |
|---|---|
| Descriptive edge | Win rate, payoff ratio, profit factor, expectancy |
| Is the mean outcome > 0? | iid and stationary bootstrap (percentile CI, null-imposed p-value); Bayesian bootstrap |
| Is the Sharpe ratio credible given fat tails? | PSR and MinTRL |
| Is the win rate above breakeven? | Beta-Binomial posterior vs breakeven rate 1/(1 + payoff) |
| Which slices are real? | One-sided t-tests per instrument x direction, Holm and BH |
| Do slices differ? | Empirical-Bayes partial pooling of win rates |
| How much to size? | Kelly growth maximisation; uncertainty via Bayesian bootstrap |
| Drawdown risk | 10,000 resampled trade sequences per leverage level |

Choices and rejected alternatives: [ADR-0006](../../decisions/ADR-0006-inference-methods.md).
Every method has a known-answer test (39 tests in total).

## 5. Results
Full tables and figures: [README, Full results](../../../README.md#full-results-testing-journal).

**5.1 The edge is statistically clear.** Mean return on notional 0.83% per trade. The iid bootstrap
CI is [0.68%, 0.98%]; the stationary bootstrap, which allows for streaks, widens it slightly to
[0.66%, 1.02%]. The Bayesian bootstrap gives P(mean <= 0) below 1 in 10,000. PSR exceeds 0.999, and
the minimum track record length needed for 95% confidence is about 44 trades, against 422 observed.

**5.2 But the profile is strongly negatively skewed.** Win rate 93.6%; average win 0.99% versus
average loss -1.48% (payoff 0.67). Skew -1.9, kurtosis 35.8. The breakeven win rate for this payoff
is 59.9%, and the posterior probability that the true win rate exceeds it is effectively 1.

**5.3 Losses are concentrated in a few large positions.** In USD the payoff ratio collapses from
0.67 to 0.15 and the profit factor from 9.8 to 2.2. The five largest losses account for 97.6% of
gross USD losses; the three largest were on positions of $0.35M to $0.81M notional. The
largest-position quartile earned 0.41% per trade, against 0.90% to 1.03% for the other three
quartiles (size-return rank correlation -0.08, p = 0.12: suggestive, not conclusive). Removing the
single worst trade raises total USD P&L from $268k to $377k.

**5.4 Slices.** All four instrument x direction slices remain significant after Holm and BH
correction. Partial pooling shrinks every slice's win rate to about 93.6%: the observed differences
(88% to 96%) are consistent with sampling noise.

**5.5 Sizing.** Full Kelly leverage is 6.7x (posterior 5th to 95th percentile 6.0x to 7.1x), almost
exactly at the 7.1x bound where a repeat of the worst trade (-14.1%) would wipe out the account.
Kelly is therefore driven by the worst observed loss, and any larger loss out of sample would be
fatal. In resampled histories at 1x leverage the median maximum drawdown is 14% and P(drawdown of
30% or more) is 0.1%; at 3x the median maximum drawdown is 42% and P(drawdown of 50% or more) is 11%.

## 6. Robustness and threats to validity
- **Regime:** the sample covers a crypto bull market and is 71% long; it says nothing about
  performance in a sustained downturn.
- **Selection:** the dataset's creator chose the accounts; the account here was selected for data
  quality, not performance, but it is still not a random trader.
- **Tail risk out of sample:** with kurtosis of 36, the worst loss in 422 trades understates the
  worst loss in the next 422. All Kelly and Monte Carlo results inherit this.
- **Independence:** iid resampling breaks streaks; the stationary bootstrap gives similar
  intervals, which suggests serial dependence is mild.
- **Outcome unit:** return on notional ignores leverage and the size decision; USD results are
  shown to expose that.

## 7. Conclusions
The testing journal shows a real, statistically robust per-trade edge that does not by itself
justify aggressive sizing. The risk lies in rare large losses on large positions. A risk manager
would cap position size and limit leverage well below half Kelly, and would focus on why the
largest positions performed worst.

## 8. Next steps
- Run the same pipeline on the personal journal (R-multiples available).
- Volatility-normalised outcomes as an alternative unit.
- Automatic block-length selection (Politis & White 2004) as a sensitivity check.

## References
See [`references.bib`](../../../references.bib).
