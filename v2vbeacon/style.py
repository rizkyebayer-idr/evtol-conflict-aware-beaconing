"""Figure styling shared by all figure scripts (paper colour scheme)."""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

#: colour of every scheme (taken from the published figures)
COLOR = {
    "fixed_high": "#E4703A",
    "proposed": "#1F5FBF",
    "rate_matched": "#E8A400",
    "fixed_low": "#14A085",
}
#: line style + marker of every scheme
STYLE = {
    "fixed_high": dict(ls="--", marker="s", dashes=(5, 2)),
    "proposed": dict(ls="-", marker="o"),
    "rate_matched": dict(ls=":", marker="D"),
    "fixed_low": dict(ls="-.", marker="^"),
}
LABEL = {
    "fixed_high": "Fixed-High (0.1 s)",
    "proposed": "Proposed (adaptive)",
    "rate_matched": "Fixed, rate-matched",
    "fixed_low": "Fixed-Low (2 s)",
}

plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "xtick.labelsize": 10.5,
    "ytick.labelsize": 10.5,
    "legend.fontsize": 10.5,
    "axes.linewidth": 0.9,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "figure.dpi": 110,
    "savefig.dpi": 220,
    "savefig.bbox": "tight",
})


def plot_series(ax, x, y, scheme, label=None, **kw):
    """Plot one scheme with its paper style."""
    style = dict(STYLE[scheme])
    style.update(kw)
    style.setdefault("markersize", 6.0)
    style.setdefault("linewidth", 2.2)
    style.setdefault("markerfacecolor", COLOR[scheme])
    style.setdefault("markeredgecolor", COLOR[scheme])
    return ax.plot(x, y, color=COLOR[scheme], label=LABEL[scheme] if label is None else label,
                   **style)[0]


def scheme_legend(fig, order, ncol=2, y=1.0):
    """Legend laid out row-wise, as in the published figures."""
    handles = [plt.Line2D([], [], color=COLOR[s], lw=2.4,
                          marker=STYLE[s]["marker"], ls=STYLE[s]["ls"],
                          markersize=6.5, label=LABEL[s]) for s in order]
    return fig.legend(handles=handles, loc="upper center", ncol=ncol,
                      bbox_to_anchor=(0.5, y), frameon=False,
                      handlelength=2.6, columnspacing=2.0)


def tidy(ax, grid=True):
    """Light horizontal grid, no top/right spines."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid:
        ax.grid(axis="y", color="0.88", lw=0.8)
        ax.set_axisbelow(True)
