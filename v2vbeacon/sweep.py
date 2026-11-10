"""Traffic-density sweep shared by Figs. 3-4 and Table II.

The expensive part of the study is the sweep over the number of eVTOLs.  It is
run once and cached in ``results/sweep_N.csv``; the figure scripts reload it.
Every sweep also runs the rate-matched baseline, whose period is by
construction the inverse of the average rate that the proposed scheme achieved
*in the same Monte Carlo run* (Sec. IV, "Baselines").
"""

from __future__ import annotations

import csv
import os
from typing import Iterable, Optional

import numpy as np

from .config import Config, N_LIST
from .engine import simulate

#: order in which the schemes appear in the figures' legend
PLOT_ORDER = ("fixed_high", "proposed", "rate_matched", "fixed_low")

FIELDS = (
    "scheme", "n", "n_runs", "rate", "rate_se", "pdr", "pdr_se", "age", "age_se",
    "age_p95", "err_p95", "err_se", "stale", "stale_se", "delay_mean",
    "delay_se", "delay_p95", "miss", "err_mean", "all_err_mean", "crit_per_veh",
)


def _row(res) -> dict:
    s = res.summary()
    return dict(
        scheme=res.scheme, n=res.n, n_runs=res.n_runs, rate=s["rate"], rate_se=s["rate_se"],
        pdr=s["pdr"], pdr_se=s["pdr_se"], age=s["age_mean"], age_se=s["age_mean_se"],
        age_p95=s["age_p95"], err_p95=s["err_p95"], err_se=s["err_p95_se"],
        stale=s["stale"], stale_se=s["stale_se"], delay_mean=s["delay_mean"],
        delay_se=s["delay_mean_se"], delay_p95=s["delay_p95"], miss=s["miss"],
        err_mean=s["err_mean"], all_err_mean=s["all_err_mean"],
        crit_per_veh=s["crit_per_veh"],
    )


def run_sweep(cfg: Config, n_list: Iterable[int] = N_LIST, n_runs: Optional[int] = None,
              verbose: bool = True, save_path: Optional[str] = None) -> list:
    """Run all four schemes for every traffic density and return the rows.

    If ``save_path`` is given the CSV is rewritten after every density, so an
    interrupted sweep can be resumed from the partial file.
    """
    rows = []
    for n in n_list:
        if verbose:
            print(f"[sweep] N = {n}", flush=True)
        prop = simulate(cfg, n, "proposed", n_runs=n_runs, verbose=verbose)
        rows.append(_row(prop))
        T_period = 1.0 / prop.rate                       # per-run rate matching
        for scheme in ("fixed_high", "fixed_low"):
            rows.append(_row(simulate(cfg, n, scheme, n_runs=n_runs, verbose=verbose)))
        rows.append(_row(simulate(cfg, n, "rate_matched", n_runs=n_runs,
                                  T_period=T_period, verbose=verbose)))
        if save_path:
            save_rows(rows, save_path)
        if verbose:
            print(f"[sweep]   done N = {n}", flush=True)
    return rows


def save_rows(rows: list, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def load_rows(path: str) -> dict:
    """Return ``{(scheme, n): {field: value}}`` from a cached CSV."""
    out = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            key = (r["scheme"], int(r["n"]))
            out[key] = {k: (float(v) if k not in ("scheme",) and v != "" else v)
                        for k, v in r.items()}
            out[key]["n"] = int(r["n"])
    return out


def load_or_run(path: str, cfg: Config, n_list: Iterable[int] = N_LIST,
                n_runs: Optional[int] = None, force: bool = False) -> dict:
    """Load the cached sweep, or run it if missing (``force`` re-runs it)."""
    if force or not os.path.exists(path):
        rows = run_sweep(cfg, n_list, n_runs=n_runs)
        save_rows(rows, path)
        return load_rows(path)
    print(f"[sweep] using cached {path} (use --force to recompute)")
    return load_rows(path)


def series(data: dict, scheme: str, field: str, n_list: Iterable[int] = N_LIST) -> np.ndarray:
    """Extract one curve ``[scheme, field]`` versus N."""
    return np.array([data[(scheme, n)][field] for n in n_list], dtype=float)
