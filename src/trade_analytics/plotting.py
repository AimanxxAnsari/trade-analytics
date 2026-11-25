"""Chart style shared by every figure in this repository.

One validated categorical palette (colour-blind-safe on adjacent pairs, checked with a
palette validator in light and dark mode), thin marks, hairline solid gridlines, left-aligned
titles, and both a light and a dark rendering of every figure:

    save_light_dark(draw, Path("figures/x.png"))  ->  x.png and x-dark.png
    picture_md("figures/x.png", "alt text")       ->  <picture> tag for GitHub READMEs

``draw(theme)`` builds and returns a figure using the colours in ``theme``.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap


@dataclass(frozen=True)
class Theme:
    name: str
    surface: str
    ink: str  # primary text
    ink2: str  # secondary text
    muted: str  # axis labels, ticks
    grid: str  # hairline gridlines
    baseline: str  # axis / zero line
    series: tuple[str, ...]  # categorical slots, fixed order
    div_neg: tuple[str, ...]  # diverging arm, dark -> light (blue)
    div_mid: str
    div_pos: tuple[str, ...]  # diverging arm, light -> dark (red)


LIGHT = Theme(
    name="light",
    surface="#fcfcfb",
    ink="#0b0b0b",
    ink2="#52514e",
    muted="#898781",
    grid="#e1e0d9",
    baseline="#c3c2b7",
    series=("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"),
    div_neg=("#104281", "#2a78d6", "#86b6ef"),
    div_mid="#f0efec",
    div_pos=("#f2a3a2", "#e34948", "#9e2726"),
)
DARK = Theme(
    name="dark",
    surface="#1a1a19",
    ink="#f0efec",
    ink2="#c3c2b7",
    muted="#898781",
    grid="#2c2c2a",
    baseline="#383835",
    series=("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"),
    div_neg=("#86b6ef", "#3987e5", "#1c5cab"),
    div_mid="#383835",
    div_pos=("#a83b3b", "#e66767", "#f2a3a2"),
)

FONT = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]


def rc(t: Theme) -> dict:
    return {
        "figure.facecolor": t.surface,
        "axes.facecolor": t.surface,
        "savefig.facecolor": t.surface,
        "font.family": "sans-serif",
        "font.sans-serif": FONT,
        "font.size": 10,
        "text.color": t.ink,
        "axes.labelcolor": t.ink2,
        "axes.labelsize": 9.5,
        "axes.titlesize": 12.5,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 22,
        "axes.edgecolor": t.baseline,
        "axes.linewidth": 1.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "axes.prop_cycle": mpl.cycler(color=list(t.series)),
        "grid.color": t.grid,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "xtick.color": t.muted,
        "ytick.color": t.muted,
        "xtick.labelcolor": t.muted,
        "ytick.labelcolor": t.muted,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "ytick.left": False,
        "xtick.major.size": 3,
        "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "lines.markersize": 7,
        "patch.linewidth": 0,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "legend.labelcolor": t.ink2,
        "figure.dpi": 110,
    }


def use(t: Theme = LIGHT) -> None:
    """Apply a theme globally (e.g. in a notebook)."""
    mpl.rcParams.update(rc(t))


@contextmanager
def themed(t: Theme):
    with plt.rc_context(rc(t)):
        yield t


def title(ax, text: str, subtitle: str | None = None, t: Theme = LIGHT) -> None:
    """Left-aligned title with an optional secondary-ink subtitle underneath."""
    ax.set_title(text, loc="left", color=t.ink, pad=24 if subtitle else 10)
    if subtitle:
        ax.text(
            0,
            1.02,
            subtitle,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=9,
            color=t.ink2,
        )


def ref_line(
    ax,
    x: float | None = None,
    y: float | None = None,
    label: str = "",
    t: Theme = LIGHT,
    color: str | None = None,
) -> None:
    """Thin solid reference line with a small direct label (no legend entry needed)."""
    c = color or t.ink2
    if x is not None:
        ax.axvline(x, color=c, lw=1.2, zorder=1)
        if label:
            ax.annotate(
                label,
                (x, 1.0),
                xycoords=("data", "axes fraction"),
                xytext=(4, -2),
                textcoords="offset points",
                ha="left",
                va="top",
                fontsize=8.5,
                color=t.ink2,
            )
    if y is not None:
        ax.axhline(y, color=c, lw=1.2, zorder=1)
        if label:
            ax.annotate(
                label,
                (1.0, y),
                xycoords=("axes fraction", "data"),
                xytext=(0, 3),
                textcoords="offset points",
                ha="right",
                va="bottom",
                fontsize=8.5,
                color=t.ink2,
            )


def end_label(ax, x, y, text: str, t: Theme = LIGHT, dx: int = 6) -> None:
    """Direct label at the end of a line, in text ink (identity comes from the line)."""
    ax.annotate(
        text,
        (x, y),
        xytext=(dx, 0),
        textcoords="offset points",
        ha="left",
        va="center",
        fontsize=8.5,
        color=t.ink2,
    )


def legend_top(ax, ncol: int = 1, t: Theme = LIGHT, loc: str = "upper right") -> None:
    """Frameless legend inside the plot area (kept clear of the title and subtitle)."""
    ax.legend(
        loc=loc,
        ncol=ncol,
        handlelength=1.4,
        borderaxespad=0.4,
        columnspacing=1.4,
        labelcolor=t.ink2,
    )


def diverging_cmap(t: Theme) -> LinearSegmentedColormap:
    colors = [*t.div_neg, t.div_mid, *t.div_pos]
    return LinearSegmentedColormap.from_list(f"div_{t.name}", colors)


def save_light_dark(draw: Callable[[Theme], plt.Figure], path: Path, dpi: int = 150) -> None:
    """Render ``draw`` in both themes: path (light) and path-dark (dark)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for t, target in ((LIGHT, path), (DARK, path.with_name(f"{path.stem}-dark{path.suffix}"))):
        with themed(t):
            fig = draw(t)
            fig.savefig(
                target,
                dpi=dpi,
                bbox_inches="tight",
                facecolor=t.surface,
                metadata={"Software": None},
            )
            plt.close(fig)


def picture_md(src: str, alt: str) -> str:
    """GitHub-friendly <picture>: dark variant for dark-mode viewers, light otherwise."""
    dark = src.replace(".png", "-dark.png")
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="{dark}">'
        f'<img src="{src}" alt="{alt}" width="100%"></picture>'
    )
