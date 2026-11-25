"""Run the full Pillar 1 analysis on a canonical trade table and write a report.

Outcome unit (ADR-0005): R-multiples when ``risk_amount`` is available,
otherwise return on entry notional (pnl / notional).
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, PercentFormatter  # noqa: E402

from trade_analytics.bayes import (  # noqa: E402
    bayesian_bootstrap_mean,
    breakeven_win_rate,
    partial_pool_win_rates,
    win_rate_posterior,
)
from trade_analytics.bootstrap import bootstrap_mean  # noqa: E402
from trade_analytics.metrics import summarise  # noqa: E402
from trade_analytics.monte_carlo import drawdown_risk, max_drawdown  # noqa: E402
from trade_analytics.multiple_testing import slice_tests  # noqa: E402
from trade_analytics.plotting import (  # noqa: E402
    Theme,
    end_label,
    legend_top,
    picture_md,
    ref_line,
    save_light_dark,
)
from trade_analytics.plotting import title as chart_title  # noqa: E402
from trade_analytics.sharpe import sharpe_summary  # noqa: E402
from trade_analytics.sizing import growth_rate, kelly_with_uncertainty  # noqa: E402


def outcome_series(trades: pd.DataFrame) -> tuple[pd.Series, str]:
    if "risk_amount" in trades.columns and trades["risk_amount"].notna().all():
        return (trades["pnl"] / trades["risk_amount"]).rename("outcome"), "R-multiple"
    if "notional" not in trades.columns:
        raise ValueError("need risk_amount or notional to define the outcome unit")
    return (trades["pnl"] / trades["notional"]).rename("outcome"), "return on notional"


def _fmt(v: float, pct: bool = False) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    if isinstance(v, float) and np.isinf(v):
        return "inf"
    return f"{v:.2%}" if pct else f"{v:.4g}"


def build_report(trades: pd.DataFrame, out_dir: str | Path, title: str) -> dict:
    out = Path(out_dir)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    x_series, unit = outcome_series(trades)
    x = x_series.to_numpy()
    pct = unit == "return on notional"

    desc = summarise(x)
    usd = summarise(trades["pnl"].to_numpy())
    boot_iid = bootstrap_mean(x, method="iid")
    boot_blk = bootstrap_mean(x, method="stationary")
    sh = sharpe_summary(x)
    post = win_rate_posterior(desc.n_wins, desc.n_trades)
    be = breakeven_win_rate(desc.payoff_ratio)
    bb = bayesian_bootstrap_mean(x)
    df = trades.assign(outcome=x)
    slices = slice_tests(df, "outcome", ["instrument", "direction"])
    grp = df.groupby(["instrument", "direction"])["outcome"]
    pooled = partial_pool_win_rates(
        [" / ".join(k) for k in grp.groups], grp.apply(lambda s: (s > 0).sum()), grp.size()
    )
    kelly = kelly_with_uncertainty(x)
    fractions = sorted({round(f, 2) for f in [1, 2, 3, kelly.point / 4, kelly.point / 2]})
    fractions = [f for f in fractions if f > 0]
    dd = drawdown_risk(x, fractions, n_paths=10_000).table
    hist_dd = float(max_drawdown(np.cumprod(1 + x)[None, :])[0])

    # ------------------------------------------------------------- figures
    figs = out / "figures"
    unit_fmt = PercentFormatter(1.0, decimals=1) if pct else None
    equity = trades.set_index("exit_time")["pnl"].cumsum()

    def draw_equity(t: Theme):
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.plot(equity.index, equity.values, color=t.series[0])
        ax.fill_between(equity.index, equity.values, 0, color=t.series[0], alpha=0.10, lw=0)
        ax.axhline(0, color=t.baseline, lw=1)
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda v, _: f"{'\u2212' if v < 0 else ''}${abs(v) / 1000:,.0f}k")
        )
        end_label(ax, equity.index[-1], equity.iloc[-1], f"${equity.iloc[-1] / 1000:,.0f}k", t)
        chart_title(ax, "Cumulative net P&L", f"USD, {len(trades)} trades, after fees", t)
        return fig

    def draw_outcomes(t: Theme):
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.hist(x, bins=70, color=t.series[0], edgecolor=t.surface, linewidth=0.6)
        ref_line(ax, x=0, label="zero", t=t)
        if unit_fmt:
            ax.xaxis.set_major_formatter(unit_fmt)
        ax.set(xlabel=unit, ylabel="trades")
        chart_title(
            ax,
            "Distribution of trade outcomes",
            f"{unit}; win rate {desc.win_rate:.1%}, mean {_fmt(desc.expectancy, pct)}",
            t,
        )
        return fig

    def draw_uncertainty(t: Theme):
        fig, ax = plt.subplots(figsize=(9, 3.6))
        draws = [
            ("iid bootstrap", boot_iid.samples),
            ("stationary bootstrap", boot_blk.samples),
            ("Bayesian bootstrap", bb),
        ]
        lowest = min(d.min() for _, d in draws)
        share_le0 = float(np.mean(np.concatenate([d for _, d in draws]) <= 0))
        bins = np.linspace(lowest, max(d.max() for _, d in draws), 70)
        for i, (label, d) in enumerate(draws):
            ax.hist(d, bins=bins, histtype="step", lw=2, color=t.series[i], label=label)
        if unit_fmt:
            ax.xaxis.set_major_formatter(unit_fmt)
        ax.set(xlabel=f"mean {unit}", ylabel="draws")
        legend_top(ax, 1, t)
        chart_title(
            ax,
            "Uncertainty in the mean outcome",
            (
                f"10,000 draws per method; lowest draw {lowest:.2%}, so no draw reaches zero"
                if lowest > 0
                else f"10,000 draws per method; {share_le0:.1%} of draws at or below zero"
            ),
            t,
        )
        return fig

    bound = 1 / -x.min() if x.min() < 0 else max(kelly.point * 2, 1.0)
    f_grid = np.linspace(0, bound * 0.999, 300)
    g = np.array([growth_rate(x, f) for f in f_grid])

    def draw_kelly(t: Theme):
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.axvspan(kelly.quantile(0.05), kelly.quantile(0.95), color=t.series[1], alpha=0.10, lw=0)
        ax.plot(f_grid, g, color=t.series[0])
        ref_line(ax, x=kelly.point, label=f"full Kelly {kelly.point:.2f}", t=t, color=t.series[1])
        ref_line(
            ax, x=kelly.point / 2, label=f"half Kelly {kelly.point / 2:.2f}", t=t, color=t.series[2]
        )
        ax.set(
            xlabel="size scale f (leverage)" if pct else "size scale f (fraction risked)",
            ylabel="expected log growth per trade",
        )
        ax.set_xlim(0, bound * 1.02)
        chart_title(
            ax,
            "Growth vs position size",
            f"Shaded: 90% posterior band for the optimum; curve ends at the wipe-out bound "
            f"{bound:.2f}",
            t,
        )
        return fig

    save_light_dark(draw_equity, figs / "equity_usd.png")
    save_light_dark(draw_outcomes, figs / "outcome_hist.png")
    save_light_dark(draw_uncertainty, figs / "mean_uncertainty.png")
    save_light_dark(draw_kelly, figs / "kelly_growth.png")

    # ------------------------------------------------------------- markdown
    f_ = lambda v: _fmt(v, pct)  # noqa: E731
    lines = [
        f"# {title}",
        "",
        "Generated by trade-analytics. All numbers are reproducible from the input",
        "journal and fixed random seeds.",
        "",
        *(
            [
                f"> **Warning:** only {desc.n_trades} trades. Bootstrap intervals, PSR, Kelly and",
                "> Monte Carlo results are unreliable below roughly 30 trades.",
                "",
            ]
            if desc.n_trades < 30
            else []
        ),
        f"- Trades: **{desc.n_trades}**",
        f"- Period: {trades['entry_time'].min():%Y-%m-%d} to {trades['exit_time'].max():%Y-%m-%d}",
        f"- Instruments: {', '.join(sorted(trades['instrument'].unique()))}",
        f"- Outcome unit: **{unit}**",
        "",
        "## 1. Descriptive statistics",
        "",
        "| Statistic | Outcome unit | USD |",
        "|---|---|---|",
        f"| Win rate | {desc.win_rate:.2%} | {usd.win_rate:.2%} |",
        f"| Average win | {f_(desc.avg_win)} | {usd.avg_win:,.0f} |",
        f"| Average loss | {f_(desc.avg_loss)} | {usd.avg_loss:,.0f} |",
        f"| Payoff ratio | {desc.payoff_ratio:.3f} | {usd.payoff_ratio:.3f} |",
        f"| Profit factor | {desc.profit_factor:.3f} | {usd.profit_factor:.3f} |",
        f"| Expectancy (mean) | {f_(desc.expectancy)} | {usd.expectancy:,.0f} |",
        f"| Std dev | {f_(desc.std)} | {usd.std:,.0f} |",
        f"| Total | {f_(desc.total)} | {usd.total:,.0f} |",
        "",
        picture_md("figures/equity_usd.png", "equity"),
        picture_md("figures/outcome_hist.png", "outcomes"),
        "",
        "## 2. Is the edge distinguishable from zero?",
        "",
        "| Method | Mean | 95% interval | one-sided p (mean <= 0) |",
        "|---|---|---|---|",
        f"| iid bootstrap | {f_(boot_iid.mean)} | [{f_(boot_iid.ci_low)}, {f_(boot_iid.ci_high)}]"
        f" | {boot_iid.p_value:.4f} |",
        f"| stationary bootstrap (L = {boot_blk.block_length:.1f}) | {f_(boot_blk.mean)} | "
        f"[{f_(boot_blk.ci_low)}, {f_(boot_blk.ci_high)}] | {boot_blk.p_value:.4f} |",
        f"| Bayesian bootstrap | {f_(float(bb.mean()))} | "
        f"[{f_(float(np.quantile(bb, 0.025)))}, {f_(float(np.quantile(bb, 0.975)))}] | "
        f"P(mean <= 0) = {float(np.mean(bb <= 0)):.4f} |",
        "",
        picture_md("figures/mean_uncertainty.png", "uncertainty"),
        "",
        "### Sharpe-ratio statistics (per trade)",
        "",
        "| Sharpe | SE (iid, Lo 2002) | Skew | Kurtosis | PSR (SR* = 0) | MinTRL (95%) |",
        "|---|---|---|---|---|---|",
        f"| {sh.sharpe:.3f} | {sh.se_iid:.3f} | {sh.skew:.2f} | {sh.kurtosis:.2f} | "
        f"{sh.psr:.4f} | {sh.min_trl:.1f} trades |",
        "",
        "## 3. Bayesian win rate",
        "",
        f"- Posterior Beta({post.alpha:.0f}, {post.beta:.0f}); mean {post.mean:.2%}, "
        f"95% interval [{post.interval()[0]:.2%}, {post.interval()[1]:.2%}]",
        f"- Breakeven win rate for payoff ratio {desc.payoff_ratio:.3f}: {be:.2%}",
        f"- P(true win rate > breakeven) = {post.prob_above(be):.4f}",
        "",
        "Partial pooling of win rates across instrument / direction:",
        "",
        "| Slice | Trades | Raw win rate | Pooled win rate |",
        "|---|---|---|---|",
        *[
            f"| {g} | {int(n)} | {r:.2%} | {p:.2%} |"
            for g, n, r, p in zip(pooled.groups, pooled.n, pooled.raw, pooled.pooled, strict=True)
        ],
        "",
        "## 4. Which slices survive multiple-testing correction?",
        "",
        f"{int(slices['p'].notna().sum())} slices tested (one-sided t-test, H1: mean > 0).",
        "",
        "| Slice | n | Mean | p | p (Holm) | p (BH) | Significant after Holm |",
        "|---|---|---|---|---|---|---|",
        *[
            f"| {r.slice} | {r.n} | {f_(r.mean)} | {_fmt(r.p)} | {_fmt(r.p_holm)} | "
            f"{_fmt(r.p_bh)} | {'yes' if r.significant_holm else 'no'} |"
            for r in slices.itertuples()
        ],
        "",
        "## 5. Position sizing (Kelly with parameter uncertainty)",
        "",
        f"Size scale f = {'leverage (notional / equity)' if pct else 'fraction of equity risked'}.",
        "",
        f"- Full Kelly (point estimate): **{kelly.point:.2f}**",
        f"- Posterior 5% / 50% / 95%: {kelly.quantile(0.05):.2f} / {kelly.quantile(0.5):.2f} / "
        f"{kelly.quantile(0.95):.2f}",
        f"- Posterior P(optimal size = 0): {kelly.prob_zero:.4f}",
        f"- Upper bound from worst trade ({f_(float(x.min()))}): f < {1 / -x.min():.2f}",
        "",
        picture_md("figures/kelly_growth.png", "kelly"),
        "",
        "## 6. Monte Carlo drawdowns and risk of ruin",
        "",
        f"10,000 iid resamples of the {desc.n_trades}-trade sequence. Ruin = equity at or below",
        f"50% of the starting value at any point. Historical max drawdown at f = 1: {hist_dd:.2%}.",
        "",
        "| f | Median final equity | Median max DD | 95th pct max DD | P(DD >= 20%) | "
        "P(DD >= 30%) | P(DD >= 50%) | P(ruin) |",
        "|---|---|---|---|---|---|---|---|",
        *[
            f"| {r.fraction:.2f} | {r.median_final_equity:.3g} | {r.median_max_dd:.1%} | "
            f"{r.p95_max_dd:.1%} | {r.p_dd_ge_20:.1%} | {r.p_dd_ge_30:.1%} | {r.p_dd_ge_50:.1%}"
            f" | {r.p_ruin:.1%} |"
            for r in dd.itertuples()
        ],
        "",
    ]
    (out / "REPORT.md").write_text("\n".join(lines))

    return {
        "unit": unit,
        "descriptive": asdict(desc),
        "bootstrap_iid": {k: v for k, v in asdict(boot_iid).items() if k != "samples"},
        "bootstrap_stationary": {k: v for k, v in asdict(boot_blk).items() if k != "samples"},
        "sharpe": asdict(sh),
        "win_rate_posterior": {
            "alpha": post.alpha,
            "beta": post.beta,
            "p_above_be": post.prob_above(be),
        },
        "kelly": {"point": kelly.point, "q05": kelly.quantile(0.05), "q50": kelly.quantile(0.5)},
    }
