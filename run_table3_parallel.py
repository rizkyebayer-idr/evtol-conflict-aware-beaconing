"""Run the four (D0, T0) settings of Table III in parallel and merge them.

Optional accelerator for ``table3_risk_scales.py --force``: one process per
setting.  Writes ``results/table3_risk_scales.json``, which
``table3_risk_scales.py`` then renders as the table.

    python run_table3_parallel.py
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from v2vbeacon.config import RISK_SCALES

RUNS = 20
N = 50

CODE = (
    "import sys, json, pathlib;sys.path.insert(0, r'{here}');"
    "from v2vbeacon import Config;"
    "from table3_risk_scales import run_point;"
    "r = run_point(Config(), {n}, {runs}, {d0}, {tau0});"
    "pathlib.Path(r'{out}').write_text(json.dumps(r))"
)


def main() -> None:
    procs = []
    t0 = time.time()
    for i, (d0, tau0) in enumerate(RISK_SCALES):
        out = HERE / "results" / f"table3_{i}.json"
        cmd = [sys.executable, "-c", CODE.format(here=HERE, n=N, runs=RUNS, d0=d0,
                                                tau0=tau0, out=out)]
        procs.append((subprocess.Popen(cmd, cwd=HERE), out))
        print(f"[t3] started D0={d0:.0f} T0={tau0:.0f}", flush=True)

    rows = []
    for p, out in procs:
        p.wait()
        rows.append(json.loads(out.read_text()))

    path = HERE / "results" / "table3_risk_scales.json"
    path.write_text(json.dumps(rows, indent=1))
    print(f"[t3] merged into {path} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
