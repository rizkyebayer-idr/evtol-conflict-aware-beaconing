"""Reproduce every figure and table of the paper in one go.

ORDER OF EXECUTION
------------------
1. run_sweep.py              density sweep, N = 10..50 (cached)
2. fig1_system_overview.py   schematic (no simulation)
3. fig2_crossing_encounter.py analytic crossing encounter
4. fig3_channel_load.py      load + PDR
5. fig4_timeliness.py        age / P95 error / detection delay
6. table2_main_results.py    Table II  (N = 50)
7. table3_risk_scales.py     Table III (D0 / T0 sensitivity)

Usage:  python run_all.py [--runs 50] [--skip-sweep]
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
STEPS = [
    ("run_sweep.py", ("--runs",)),
    ("fig1_system_overview.py", ()),
    ("fig2_crossing_encounter.py", ()),
    ("fig3_channel_load.py", ("--runs",)),
    ("fig4_timeliness.py", ("--runs",)),
    ("table2_main_results.py", ("--runs",)),
    ("table3_risk_scales.py", ()),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=50)
    ap.add_argument("--skip-sweep", action="store_true",
                    help="reuse results/sweep.csv and results/table3_risk_scales.json")
    a = ap.parse_args()

    for script, takes_runs in STEPS:
        if a.skip_sweep and script == "run_sweep.py":
            print(f"--- skip {script}")
            continue
        cmd = [sys.executable, "-u", str(HERE / script)]
        if takes_runs:
            cmd += ["--runs", str(a.runs)]
        print(f"--- {script}", flush=True)
        t0 = time.time()
        r = subprocess.run(cmd, cwd=HERE)
        print(f"--- {script}: exit {r.returncode} in {time.time() - t0:.0f} s", flush=True)
        if r.returncode:
            sys.exit(r.returncode)


if __name__ == "__main__":
    main()
