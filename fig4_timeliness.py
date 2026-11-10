"""FIGURE 4 - Timeliness of neighbour information in critical encounters.

WHAT THE PAPER CLAIMS
---------------------
(a) Mean age of information over critical ordered pairs: about 1 s with
    Fixed-Low, 0.54-0.55 s with the proposed rule (flat in N) and 0.18 s with
    Fixed-High, which pays for it with an order of magnitude more beacons.
(b) 95th-percentile dead-reckoning position error: 3.8-4.7 m (Fixed-Low),
    1.2-1.4 m (proposed) and 0.2 m (Fixed-High).
(c) Mean conflict-detection delay of eq. (9): 0.62-0.67 s (Fixed-Low),
    0.37-0.41 s (proposed) and 0.03-0.10 s (Fixed-High).
The decisive comparison is the rate-matched curve: at the *same* message budget
the proposed rule delivers 12-29 % fresher information and 27-50 % lower tail
error, so the benefit comes from when the messages are sent, not how many.

WHERE IN THE PAPER
------------------
Fig. 4, Sec. V-B and Sec. V-C, eq. (9); metric definitions in Table I/Sec. IV.

HOW TO READ THIS PROGRAM
------------------------
1. A "critical ordered pair" (i, j) is an in-range pair whose *true* 3-D state
   satisfies DCPA <= 100 m and 0 <= TCPA <= 15 s, sampled every 0.1 s; the age
   and the error are what receiver i knows about neighbour j at that instant.
2. The delay runs from the first instant the true states are critical to the
   first instant i's dead-reckoned estimate declares them critical; encounters
   shorter than 1 s are discarded and undetected ones count as missed.  All of
   this is implemented in `v2vbeacon.engine.simulate`, not here.
3. This script only loads the sweep and plots one column of it per panel.

INPUT / OUTPUT
--------------
Input: results/sweep.csv (pass --force to recompute).  Output:
results/fig4_timeliness.png plus the printed improvement percentages.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from v2vbeacon import Config
from v2vbeacon.config import N_LIST
from v2vbeacon.style import plt, plot_series, scheme_legend, tidy
from v2vbeacon.sweep import PLOT_ORDER, load_or_run, series

HERE = pathlib.Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=50)
    ap.add_argument("--force", action="store_true", help="recompute the sweep")
    ap.add_argument("--csv", default=str(HERE / "results" / "sweep.csv"))
    ap.add_argument("--out", default=str(HERE / "results" / "fig4_timeliness.png"))
    a = ap.parse_args()

    data = load_or_run(a.csv, Config(), N_LIST, n_runs=a.runs, force=a.force)
    n = np.array(N_LIST, dtype=float)

    fig, axes = plt.subplots(3, 1, figsize=(6.0, 7.6), sharex=True,
                             gridspec_kw=dict(hspace=0.12))

    # ------------------------------------------------ (a) mean age of information
    for s in PLOT_ORDER:
        plot_series(axes[0], n, series(data, s, "age"), s)
    axes[0].set_ylabel("Mean age [s]")
    axes[0].set_ylim(-0.04, 1.34)
    axes[0].set_yticks([0.0, 0.5, 1.0])

    # ------------------------------------- (b) 95th-percentile dead-reckoning error
    for s in PLOT_ORDER:
        plot_series(axes[1], n, series(data, s, "err_p95"), s)
    axes[1].set_ylabel("P95 pos. error [m]")
    axes[1].set_ylim(-0.20, 6.30)
    axes[1].set_yticks([0, 2, 4])

    # ------------------------------------------------- (c) conflict-detection delay
    for s in PLOT_ORDER:
        plot_series(axes[2], n, series(data, s, "delay_mean"), s)
    axes[2].set_ylabel("Mean det. delay [s]")
    axes[2].set_xlabel("Number of eVTOLs $N$")
    axes[2].set_ylim(-0.03, 0.94)
    axes[2].set_yticks([0.0, 0.25, 0.50, 0.75])

    for ax in axes:
        tidy(ax)
        ax.set_xlim(7, 53)
    axes[2].set_xticks(list(N_LIST))

    for ax, lab in zip(axes, ("(a)", "(b)", "(c)")):
        ax.text(0.045, 0.88, lab, transform=ax.transAxes, fontsize=14, va="top")

    scheme_legend(fig, PLOT_ORDER, ncol=2, y=1.0)
    fig.subplots_adjust(top=0.87)
    fig.savefig(a.out)
    print(f"written {a.out}")

    # ---------------------------------------------------------- diagnostics
    prop = series(data, "proposed", "age")
    match = series(data, "rate_matched", "age")
    print("mean critical age: proposed", np.round(prop, 3), " rate-matched", np.round(match, 3))
    print(f"improvement vs rate-matched: {100 * (1 - prop / match).min():.0f}"
          f"-{100 * (1 - prop / match).max():.0f}%")
    ep = series(data, "proposed", "err_p95")
    em = series(data, "rate_matched", "err_p95")
    print(f"P95 error improvement vs rate-matched: {100 * (1 - ep / em).min():.0f}"
          f"-{100 * (1 - ep / em).max():.0f}%")


if __name__ == "__main__":
    main()
