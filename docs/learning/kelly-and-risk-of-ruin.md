# Kelly sizing, drawdowns and risk of ruin

## Kelly criterion (Kelly 1956)
Each trade multiplies equity by (1 + f x), where x is the outcome and f the size scale (fraction
risked, or leverage). After many trades, equity grows at rate

    g(f) = E[ log(1 + f x) ]

Kelly chooses the f that maximises g.

**Binary case** (win b with probability p, lose 1 otherwise):
g(f) = p log(1 + f b) + q log(1 - f). Setting g'(f) = 0 gives

    f* = p - q / b

Example: p = 0.6, b = 1 gives f* = 0.2. Checked in `tests/test_risk_sizing.py`.

**Shape of g(f):** it rises to f*, falls back to zero at about 2f*, and is negative beyond that.
Over-betting is far worse than under-betting: **half Kelly keeps about 75% of the growth with much
smaller drawdowns** (textbook quadratic approximation; on the skewed testing journal it keeps about 58%).

**Hard upper bound:** if any outcome x_min < 0, then f must stay below 1/|x_min|, or a repeat of that
trade wipes out the account (log of 0).

## Parameter uncertainty
f* is computed from estimated outcomes, so it is uncertain. The repo re-optimises f* under many
Bayesian-bootstrap weightings of the trades. The spread of f* shows how fragile the point
estimate is; this is the main argument for fractional Kelly (MacLean, Thorp & Ziemba 2011).

**Testing journal lesson:** Kelly leverage of 6.7x sits just below the 7.1x wipe-out bound set by
the single worst trade (-14.1%). Kelly is "optimal" only if no worse trade ever happens. With
kurtosis of 36, one will.

## Drawdowns and risk of ruin by Monte Carlo
1. Resample the outcome sequence (here 10,000 times).
2. Build equity paths: E_t = E_{t-1} (1 + f x_t).
3. Max drawdown of a path = max over t of (1 - E_t / running peak).
4. Risk of ruin = share of paths that ever fall to or below a ruin level (here 50%).

The historical order of trades is one draw among many. Monte Carlo shows the range of drawdowns
the same edge could have produced.
