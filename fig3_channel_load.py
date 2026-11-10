"""FIGURE 3 - Channel load and reliability versus traffic density.

WHAT THE PAPER CLAIMS
---------------------
(a) Fixed 10-Hz beaconing puts 10 N messages per second on the channel (500
msg/s at N = 50) and congests it, whereas the proposed rule settles between
0.65 and 0.92 beacons per aircraft per second - 90.8-93.5 % fewer than
Fixed-High and only 1.3-1.8 times the Fixed-Low load.  The rate-matched
baseline necessarily overlaps the proposed curve in this panel.
(b) Under the unslotted random-access channel the packet delivery ratio of
Fixed-High collapses from 0.82 (N = 10) to 0.41 (N = 50); the proposed rule
keeps it near 0.91, essentially the same as a fixed schedule with the same
message budget, because it does not send more messages - it sends them at
better times.

WHERE IN THE PAPER
------------------
Fig. 3, Sec. V-A; channel model in Sec. II-B; baselines and metrics in Sec. IV.

HOW TO READ THIS PROGRAM
------------------------
1. `load_or_run()` returns the cached density sweep (results/sweep.csv) or
   runs it when the file is missing - see `v2vbeacon/sweep.py`, `run_sweep.py`.
2. Panel (a) plots rate * N, i.e. the total number of beacons per second on the
   channel (log scale); panel (b) plots the PDR of the same four schemes.
3. Each point is the mean over the Monte Carlo runs of Table I (50 by default).
No physics lives in the plotting code: every value comes from
`v2vbeacon.engine.simulate`.

INPUT / OUTPUT
--------------
Input: results/sweep.csv (pass --force to recompute, ~25 min with
run_sweep_parallel.py).  Output: results/fig3_channel_load.png plus a printed
summary of the curves.
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
    ap.add_argument("--out", default=str(HERE / "results" / "fig3_channel_load.png"))
    a = ap.parse_args()

    data = load_or_run(a.csv, Config(), N_LIST, n_runs=a.runs, force=a.force)
    n = np.array(N_LIST, dtype=float)

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(6.0, 5.9), sharex=True, gridspec_kw=dict(hspace=0.10))

    # ------------------------------------------------ (a) load on the channel
    for s in PLOT_ORDER:
        plot_series(ax1, n, series(data, s, "rate") * n, s)
    ax1.set_yscale("log")
    ax1.set_ylabel("Beacons on channel [msg/s]")
    ax1.set_ylim(3, 800)
    ax1.set_yticks([10, 100])
    ax1.set_yticklabels(["$10^1$", "$10^2$"])
    tidy(ax1)

    # -------------------------------------------------- (b) delivery ratio
    for s in PLOT_ORDER:
        plot_series(ax2, n, series(data, s, "pdr"), s)
    ax2.set_xlabel("Number of eVTOLs $N$")
    ax2.set_ylabel("Packet delivery ratio")
    ax2.set_ylim(0.34, 1.03)
    ax2.set_yticks([0.4, 0.6, 0.8, 1.0])
    tidy(ax2)

    ax1.set_xlim(7, 53)
    ax2.set_xticks(list(N_LIST))

    ax1.text(0.045, 0.86, "(a)", transform=ax1.transAxes, fontsize=14, va="top")
    ax2.text(0.045, 0.12, "(b)", transform=ax2.transAxes, fontsize=14, va="top")

    scheme_legend(fig, PLOT_ORDER, ncol=2, y=1.005)
    fig.subplots_adjust(top=0.86)
    fig.savefig(a.out)
    print(f"written {a.out}")

    # ---------------------------------------------------------- diagnostics
    for s in PLOT_ORDER:
        print(f"{s:13s} load {series(data, s, 'rate') * n} msg/s  "
              f"pdr {np.round(series(data, s, 'pdr'), 3)}")
    rng = 100 * (1 - series(data, "proposed", "rate") / 10.0)
    print(f"proposed: {rng.min():.1f}-{rng.max():.1f}% fewer beacons than Fixed-High")


if __name__ == "__main__":
    main()
