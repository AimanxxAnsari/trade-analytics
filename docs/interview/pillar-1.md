# Interview pack — trade-analytics

*Grows as the project progresses. Practise answering without notes.*

## 30-second pitch
*(Draft once results exist.)* "I took my own record of ~300 trades and asked the question a prop
firm would: is there real skill, or is it noise? I built the analysis like a research project —
validated data, bootstrap and Bayesian inference on the edge, multiple-testing control, and Monte
Carlo risk of ruin — and used the result to choose a position size."

## Likely questions (answers to be written in my own words)
1. Why measure outcomes in R-multiples rather than currency?
2. How did you treat breakeven trades, and why does it matter? *(ADR-0003)*
3. Why does the expectancy identity `E = p·W − q·L` need p and q over all trades?
4. Why keep the raw data out of the repo, and how do you test without it? *(ADR-0001)*
5. Why validate the whole table and report every error instead of failing on the first?
6. Why timezone-aware timestamps?
7. What is a property-based test and what does yours check?

## Must be able to rebuild from scratch
- [ ] Win rate, payoff ratio, profit factor, expectancy — and the identity between them.
- [ ] R-multiple calculation from entry, stop and size.

## Numbers to remember
*(Pending results.)*

## STAR stories
*(Pending — e.g. a data-quality issue found by validation.)*
