"""Run the traffic-density sweep of Table I / Figs. 3-4 / Table II.

WHAT THIS PROGRAM DOES
----------------------
For every traffic density N = 10, 20, 30, 40, 50 it simulates the four schemes
of Sec. IV - proposed, Fixed-High (0.1 s), Fixed-Low (2 s) and the rate-matched
fixed schedule - for the number of Monte Carlo runs of Table I (50 by default)
and stores the metrics of Sec. IV in results/sweep.csv.  The rate-matched
period is the reciprocal of the average rate the proposed scheme achieved in
the same runs, so that the comparison is at an equal message budget.

This is the only expensive step (~1.5 h serial, ~25 min with
`run_sweep_parallel.py`, which runs one process per density).  Figures 3-4 and
Table II reuse the cached CSV.

INPUT / OUTPUT
--------------
Output: results/sweep.csv (rewritten after every density, so an interrupted
run resumes from a partial file).
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from v2vbeacon import Config
from v2vbeacon.config import N_LIST
from v2vbeacon.sweep import run_sweep

HERE = pathlib.Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=50, help="Monte Carlo runs per configuration")
    ap.add_argument("--n", type=int, nargs="+", default=list(N_LIST), help="traffic densities")
    ap.add_argument("--out", default=str(HERE / "results" / "sweep.csv"))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    t0 = time.time()
    run_sweep(Config(), a.n, n_runs=a.runs, verbose=not a.quiet, save_path=a.out)
    print(f"[sweep] written to {a.out} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
