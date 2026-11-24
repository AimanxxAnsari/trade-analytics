# Expectancy and R-multiples

## R-multiples
A trade's outcome divided by the amount planned to be risked:

    R = P&L / risk_amount,   risk_amount = |entry − stop| × size × multiplier

R normalises trades of different sizes and instruments onto one scale: −1R is a full planned loss,
+2R is twice the planned risk won.

## Expectancy
With n trades, w wins, l losses and s scratches (n = w + l + s):

    E = mean(R) = (Σ wins + Σ losses) / n
      = (w/n)·avg_win − (l/n)·|avg_loss|
      = p·W − q·L

p and q are rates over **all** trades, so p + q ≤ 1 when scratches exist. Using p and q over
wins+losses only would silently overstate E when scratches are common.

## Related quantities
- **Payoff ratio** W/L: how big wins are relative to losses.
- **Profit factor** Σwins / |Σlosses| = (p·W)/(q·L). PF > 1 ⇔ E > 0.
- **Breakeven win rate** for a payoff ratio b (no scratches): p* = 1/(1 + b).

## Caveat
These are point estimates. With ~300 trades the sampling error of E is large — the next modules
(bootstrap, Bayesian) quantify it.
