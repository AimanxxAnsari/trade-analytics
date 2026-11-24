# Bootstrap, Bayesian bootstrap and the Probabilistic Sharpe Ratio

## Bootstrap (Efron 1979)
We observe n trade outcomes and want the uncertainty of their mean without assuming a
distribution.

1. Draw n outcomes **with replacement** from the sample; compute the mean.
2. Repeat B times (e.g. 10,000) to get the bootstrap distribution of the mean.
3. **95% percentile CI** = 2.5th and 97.5th percentiles of those means.

Why it works: the sample is our best estimate of the population, so resampling from it mimics
drawing new samples from the population.

**p-value for H0: mean <= 0.** Shift the bootstrap means so they average zero (imposing the null),
then count how often a shifted mean is at least the observed mean:
`p = (#{m_b - mean >= mean} + 1) / (B + 1)`. The +1 avoids reporting p = 0.

## Stationary bootstrap (Politis & Romano 1994)
If outcomes cluster (winning or losing streaks), resampling single trades destroys that structure
and makes the CI too narrow. Instead resample **blocks** of consecutive trades. In the stationary
version, block lengths are random (geometric with mean L): at each step, continue the current
block with probability 1 - 1/L or jump to a random new start with probability 1/L. Indices wrap
around the end. Rule of thumb: L ~ n^(1/3).

Test in the repo: on an AR(1) series with coefficient 0.7 the block CI is more than 1.5x wider than
the iid CI.

## Bayesian bootstrap (Rubin 1981)
Instead of integer resampling counts, give each trade a random weight from a Dirichlet(1, ..., 1)
distribution (positive weights that sum to 1). Each weighted mean is a draw from the posterior of
the mean under a non-parametric model. Gives P(mean > 0) directly.

## Sharpe ratio and its uncertainty
- Per-trade Sharpe SR = mean / std.
- Under iid normal outcomes, SE(SR) ~ sqrt((1 + SR^2 / 2) / n) (Lo 2002).

## Probabilistic Sharpe Ratio (Bailey & López de Prado 2012)
The probability that the true Sharpe exceeds a benchmark SR*, accounting for skewness g3 and
kurtosis g4 (non-excess):

    PSR = Phi( (SR - SR*) * sqrt(n - 1) / sqrt(1 - g3*SR + (g4 - 1)/4 * SR^2) )

Negative skew and high kurtosis **enlarge the denominator**, so PSR falls: a fat-tailed record needs
more trades to be convincing.

**Minimum Track Record Length**: the n at which PSR reaches 1 - alpha:

    MinTRL = 1 + (1 - g3*SR + (g4 - 1)/4 * SR^2) * (z_{1-alpha} / (SR - SR*))^2

Testing journal: SR = 0.53, g3 = -1.9, g4 = 35.8 gives MinTRL of about 44 trades. A normal
distribution with the same SR would need only about 12.
