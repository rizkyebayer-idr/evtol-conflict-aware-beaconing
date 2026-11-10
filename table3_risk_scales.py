"""TABLE III - Sensitivity to the risk scales D0 and T0 at N = 50.

WHAT THE PAPER REPORTS
----------------------
Moving the pair (D0, T0) moves the scheme along the load/timeliness trade-off:
larger scales react earlier and more strongly (higher beacon rate, lower age),
smaller scales save messages.  At every setting the proposed rule still beats a
fixed schedule with the *same* average rate, so (D0, T0) is one interpretable
knob and the benefit of risk awareness is preserved.

WHERE IN THE PAPER
------------------
Table III, Sec. V-D, eqs. (5)-(8).

HOW TO READ THIS PROGRAM
------------------------
1. `run_point()` runs the proposed scheme for one (D0, T0) and immediately the
   rate-matched baseline whose period is the reciprocal of the rate the
   proposed scheme reached in the very same runs (`T_period=1/rate`), so the
   two columns of a row are always comparable.
2. The four settings are `v2vbeacon.config.RISK_SCALES`.  Results are cached in
   results/table3_risk_scales.json; use --force to recompute (~15 min, or
   `run_table3_parallel.py` for ~4 min).

INPUT / OUTPUT
--------------
Output: results/table3_risk_scales.md plus the json cache.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from v2vbeacon import Config, simulate
from v2vbeacon.config import RISK_SCALES

HERE = pathlib.Path(__file__).resolve().parent


def run_point(cfg: Config, n: int, n_runs: int, d0: float, tau0: float) -> dict:
    c = cfg.with_(d0=d0, tau0=tau0)
    prop = simulate(c, n, "proposed", n_runs=n_runs)
    match = simulate(c, n, "rate_matched", n_runs=n_runs, T_period=1.0 / prop.rate)
    return dict(d0=d0, tau0=tau0, n=n, n_runs=n_runs,
                rate=prop.summary()["rate"],
                age_prop=prop.summary()["age_mean"],
                age_match=match.summary()["age_mean"],
                err_prop=prop.summary()["err_p95"],
                err_match=match.summary()["err_p95"],
                stale_prop=prop.summary()["stale"],
                stale_match=match.summary()["stale"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--runs", type=int, default=20, help="runs per setting (Table III uses 20)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--cache", default=str(HERE / "results" / "table3_risk_scales.json"))
    ap.add_argument("--out", default=str(HERE / "results" / "table3_risk_scales.md"))
    a = ap.parse_args()

    cache = pathlib.Path(a.cache)
    if cache.exists() and not a.force:
        print(f"[table3] using cached {cache} (use --force to recompute)")
        rows = json.loads(cache.read_text())
    else:
        rows = []
        t0 = time.time()
        for d0, tau0 in RISK_SCALES:
            print(f"[table3] D0 = {d0:.0f} m, T0 = {tau0:.0f} s", flush=True)
            rows.append(run_point(Config(), a.n, a.runs, d0, tau0))
            cache.write_text(json.dumps(rows, indent=1))
        print(f"[table3] done in {time.time() - t0:.0f} s")

    head = ("| $D_0$ / $T_0$ [m/s] | Rate [msg/s/veh] | Crit. age Prop. [s] "
            "| Crit. age Match [s] | Stale Prop. [%] | Stale Match [%] |")
    lines = [f"TABLE III  --  Sensitivity to D0/T0 at N = {a.n} "
             f"({a.runs} runs each)", head, "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['d0']:.0f} / {r['tau0']:.0f} | {r['rate']:.2f} "
                     f"| {r['age_prop']:.2f} | {r['age_match']:.2f} "
                     f"| {100 * r['stale_prop']:.1f} | {100 * r['stale_match']:.1f} |")

    text = "\n".join(lines)
    print(text)
    gain = [100 * (1 - r["age_prop"] / r["age_match"]) for r in rows]
    gain_e = [100 * (1 - r["err_prop"] / r["err_match"]) for r in rows]
    print(f"\nage advantage over the rate-matched schedule: {min(gain):.0f}-{max(gain):.0f}%")
    print(f"P95 error advantage: {min(gain_e):.0f}-{max(gain_e):.0f}%")
    pathlib.Path(a.out).write_text(text + "\n")
    print(f"written {a.out}")


if __name__ == "__main__":
    main()
