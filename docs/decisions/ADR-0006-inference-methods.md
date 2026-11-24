# ADR-0006: Inference methods and defaults

- **Date:** 2026-11-24
- **Status:** accepted

## Context
Trade outcomes are fat-tailed, skewed and possibly serially dependent. The sample is a few hundred
trades. Methods must be honest under those conditions and simple enough to explain.

## Decisions
| Question | Choice | Rejected alternative and why |
|---|---|---|
| CI for the mean | Percentile bootstrap, **both** iid and stationary | t-interval only: assumes near-normality, which fails at kurtosis 36 |
| Block length | L = n^(1/3) rule of thumb | Politis-White automatic selection: more complex; can be added if results are sensitive |
| p-value | Shifted (null-imposed) bootstrap, one-sided, with +1 correction | Fraction of bootstrap means <= 0: not a valid p-value |
| Sharpe significance | PSR and MinTRL (skew/kurtosis aware) | Plain t-stat on Sharpe: ignores fat tails |
| Win-rate uncertainty | Beta(1, 1) prior, Beta-Binomial posterior | Normal approximation: poor near 0 or 1 (win rate here is 94%) |
| Mean posterior | Bayesian bootstrap (Rubin 1981) | Parametric model: would need a fat-tailed likelihood choice |
| Slices | One-sided t per slice, Holm (FWER) and BH (FDR) both reported | Uncorrected p-values |
| Group win rates | Empirical-Bayes partial pooling (method of moments) | Full hierarchical MCMC: heavy dependency for little gain at 4 groups |
| Sizing uncertainty | Kelly re-optimised per Bayesian-bootstrap draw | Single point-estimate Kelly |
| Monte Carlo | iid resampling, 10,000 paths, fixed seed | Parametric simulation: would impose a distribution |

All random procedures take a `seed` (default 0) so reports are reproducible.

## Consequences
- Every method has a known-answer test (coverage, closed forms, hand calculations).
- The Kelly upper bound is set by the worst observed trade; out-of-sample losses can be larger,
  which the write-up must state.
