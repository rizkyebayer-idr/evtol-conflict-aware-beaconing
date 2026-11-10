"""Run the density sweep of N = 10..50 as one process per density (parallel).

Optional accelerator for ``run_sweep.py``: the numerics are identical, only the
wall-clock time changes (one process per N on a multi-core machine).  Each child
writes ``results/sweep_N<n>.csv``; this driver merges them into
``results/sweep.csv`` in the canonical order.

    python run_sweep_parallel.py 50
"""

from __future__ import annotations

import csv
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
N_LIST = (10, 20, 30, 40, 50)


def main() -> None:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    procs = []
    t0 = time.time()
    for n in N_LIST:
        out = HERE / "results" / f"sweep_N{n}.csv"
        log = open(HERE / "results" / f"sweep_N{n}.log", "w")
        p = subprocess.Popen(
            [sys.executable, "-u", str(HERE / "run_sweep.py"), "--runs", str(runs),
             "--n", str(n), "--out", str(out), "--quiet"],
            stdout=log, stderr=subprocess.STDOUT, cwd=HERE)
        procs.append((n, p, log))
        print(f"[par] started N = {n} (pid {p.pid})", flush=True)

    for n, p, log in procs:
        rc = p.wait()
        log.close()
        print(f"[par] N = {n} finished rc = {rc} at {time.time() - t0:.0f} s", flush=True)

    rows, fields = [], None
    for n in N_LIST:
        with open(HERE / "results" / f"sweep_N{n}.csv", newline="") as fh:
            rd = csv.DictReader(fh)
            fields = rd.fieldnames
            rows.extend(rd)
    if "n_runs" not in fields:
        fields.insert(fields.index("n") + 1, "n_runs")
        for r in rows:
            r["n_runs"] = runs
    with open(HERE / "results" / "sweep.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"[par] merged {len(rows)} rows into results/sweep.csv in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
