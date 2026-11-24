# Skill or luck? A statistical assessment of a discretionary trading record

*Working paper — draft. Sections fill in as modules are completed.*

## Abstract
*(To be written when results exist.)*

## 1. Introduction
Prop firms, hedge funds and allocators must decide from a limited track record whether a trader
has an edge and how much capital to give them. With a few hundred trades, fat-tailed outcomes and
many possible ways to slice the record, it is easy to mistake luck for skill. This project applies
standard inference tools to one discretionary record (~300 trades in equity index, crude oil, gold
and FX) and asks what can and cannot be concluded.

**Who uses this in industry:** prop-trading firms and funded-trader programmes (allocation and
drawdown limits), multi-manager funds (manager evaluation), risk teams (position-size caps).

## 2. Related work
- Expectancy and R-multiples as the unit of trade analysis (Tharp).
- Sampling uncertainty of the Sharpe ratio (Lo 2002); Probabilistic Sharpe Ratio and Minimum
  Track Record Length (Bailey & López de Prado 2012).
- Bootstrap inference (Efron 1979) and the stationary bootstrap for dependent data
  (Politis & Romano 1994).
- Multiple-testing control (Holm 1979; Benjamini & Hochberg 1995).
- Log-optimal sizing (Kelly 1956; Thorp 2006) and fractional Kelly (MacLean, Thorp & Ziemba 2011).
- Evidence on retail and day-trader skill (Barber & Odean 2000; Barber, Lee, Liu & Odean 2014).

## 3. Data
Personal journal export, mapped to the canonical schema in
[`docs/design/trade-schema.md`](../../design/trade-schema.md). Raw data stays private
([ADR-0001](../../decisions/ADR-0001-private-trade-data.md)). *Period, instruments, cleaning steps
and exclusions to be documented once loaded.*

## 4. Method
| Question | Method | Module |
|---|---|---|
| Descriptive edge | Win rate, payoff, profit factor, expectancy in R | `metrics` ✅ |
| Is the edge ≠ 0? | Bootstrap CI; t-test; PSR; MinTRL | `bootstrap`, `sharpe` |
| P(edge > 0) | Beta-Binomial + hierarchical model | `bayes` |
| Which slices are real? | Holm / BH correction; number of slices reported | `multiple_testing` |
| Drawdown risk | Trade-sequence Monte Carlo; risk of ruin | `monte_carlo` |
| How much to risk? | Kelly under posterior uncertainty | `sizing` |

**Pre-registration:** hypotheses and decision rules will be written as an ADR before the main
inference run.

## 5. Results
*(Pending.)*

## 6. Robustness
*(Pending: by period, by instrument, with/without largest trades, block vs iid bootstrap.)*

## 7. Limitations
- Single trader, ~300 trades: low power by construction.
- Regime dependence: the sample covers specific market conditions.
- Self-recorded journal: possible recording errors; checked by schema validation.

## References
See [`references.bib`](../../../references.bib).
