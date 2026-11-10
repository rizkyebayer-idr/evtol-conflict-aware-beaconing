"""TABLE II - Performance at N = 50 (mean of the Monte Carlo runs).

WHAT THE PAPER REPORTS
----------------------
One row per scheme (Fixed-High, Fixed-Low, rate-matched, proposed) with the
metrics of Sec. IV: beacon rate per aircraft, packet delivery ratio, mean age
and 95th-percentile dead-reckoning error over critical pairs, stale fraction,
and the mean/P95 conflict-detection delay of eq. (9).
How to read it: the proposed row has almost the same rate and PDR as the
rate-matched row but a lower age, a lower tail error and a smaller stale
fraction, and it is an order of magnitude below Fixed-High in rate.

WHERE IN THE PAPER
------------------
Table II, Sec. V, Table I, eq. (9).

HOW TO READ THIS PROGRAM
------------------------
It loads the cached density sweep and prints the row of every scheme at N = 50;
each number is the mean over the Monte Carlo runs.  Nothing is computed here -
the metrics are produced by `v2vbeacon.engine.simulate`, so the table and
Figs. 3-4 can never disagree.

INPUT / OUTPUT
--------------
Input: results/sweep.csv.  Output: results/table2_main_results.md and stdout.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from v2vbeacon import Config
from v2vbeacon.config import N_LIST
from v2vbeacon.sweep import load_or_run

HERE = pathlib.Path(__file__).resolve().parent

#: row order of Table II
ROWS = (("fixed_high", "Fixed-High"), ("fixed_low", "Fixed-Low"),
        ("rate_matched", "Rate-matched"), ("proposed", "Proposed"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=50, help="traffic density of the table")
    ap.add_argument("--runs", type=int, default=50)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--csv", default=str(HERE / "results" / "sweep.csv"))
    ap.add_argument("--out", default=str(HERE / "results" / "table2_main_results.md"))
    a = ap.parse_args()

    data = load_or_run(a.csv, Config(), N_LIST, n_runs=a.runs, force=a.force)

    head = ("| Scheme | Rate [msg/s/veh] | PDR | Crit. age [s] | Crit. P95 err. [m] "
            "| Stale [%] | Det. delay [s] mean / P95 |")
    sep = "|---|---|---|---|---|---|---|"
    lines = [f"TABLE II  --  Performance at N = {a.n} "
             f"(mean of {int(data[(ROWS[0][0], a.n)].get('n_runs', a.runs))} runs)", head, sep]
    csv_rows = []
    for key, name in ROWS:
        d = data[(key, a.n)]
        lines.append(
            f"| {name} | {d['rate']:.2f} | {d['pdr']:.2f} | {d['age']:.2f} "
            f"| {d['err_p95']:.2f} | {100 * d['stale']:.1f} "
            f"| {d['delay_mean']:.2f} / {d['delay_p95']:.2f} |")
        csv_rows.append(dict(scheme=key, rate=d["rate"], pdr=d["pdr"], age=d["age"],
                             err_p95=d["err_p95"], stale=100 * d["stale"],
                             delay_mean=d["delay_mean"], delay_p95=d["delay_p95"],
                             miss=100 * d["miss"], err_mean=d["err_mean"],
                             all_err_mean=d["all_err_mean"],
                             crit_per_veh=d["crit_per_veh"]))

    text = "\n".join(lines)
    print(text)
    print()
    print(f"critical neighbours per aircraft: {csv_rows[-1]['crit_per_veh']:.2f}")
    print(f"missed critical encounters: Fixed-Low {csv_rows[1]['miss']:.1f}%, "
          f"Proposed {csv_rows[-1]['miss']:.1f}%")
    print(f"mean error over all in-range pairs at N = {a.n}: "
          f"rate-matched {csv_rows[2]['all_err_mean']:.2f} m, "
          f"proposed {csv_rows[3]['all_err_mean']:.2f} m")

    pathlib.Path(a.out).write_text(text + "\n")
    print(f"written {a.out}")


if __name__ == "__main__":
    main()
