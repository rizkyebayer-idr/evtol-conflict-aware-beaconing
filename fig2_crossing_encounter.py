"""FIGURE 2 - A single loss-free crossing encounter (the mechanism in action).

WHAT THE PAPER CLAIMS
---------------------
eVTOL i (40 m/s, east) and eVTOL j (30 m/s, north) cross with a predicted miss
distance DCPA = 25 m at t = 40 s; perfect knowledge and no packet loss.  Far
from the CPA the interval stays close to T_max.  Because the risk
R_i = exp(-DCPA/D0) exp(-TCPA/T0) grows towards exp(-25/150) = 0.85, the
interval falls below 1 s about 32.9 s into the scenario and reaches 0.40 s just
before the CPA; afterwards TCPA < 0, the risk drops to zero and the interval
returns immediately to T_max.  Over the 60-s window eVTOL i sends 42 beacons
instead of 600 (fixed 10 Hz) or 30 (fixed 0.5 Hz), and the extra messages are
concentrated in the last seconds before the encounter.

WHERE IN THE PAPER
------------------
Fig. 2, Sec. III-B, eqs. (3)-(8), Algorithm 1.

HOW TO READ THIS PROGRAM
------------------------
1. `P_I0`, `P_J0`, `V_I`, `V_J` define the encounter.  The starting positions
   are chosen so that r(40 s) = (15, 20, 0) m, i.e. |r| = DCPA = 25 m exactly
   and TCPA(t) = 40 - t exactly (checked by the printed diagnostics).
2. The script evaluates (3)-(4) with `pairwise_geometry`, (5)-(6) with
   `conflict_risk` and (8) with `risk_to_interval` - the same functions the
   full simulator uses, so the figure cannot drift away from the model.
3. `beacon_instants()` is Algorithm 1, lines 11-12: broadcast whenever
   t - t_last >= T_i(t).  Beacons are counted over [0, 60).
Everything here is analytic: no Monte Carlo, no channel model, no randomness.

INPUT / OUTPUT
--------------
No input.  Prints the numbers quoted in the text and writes
results/fig2_crossing_encounter.png.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from v2vbeacon import Config
from v2vbeacon.geometry import conflict_risk, pairwise_geometry, risk_to_interval
from v2vbeacon.style import plt, tidy

HERE = pathlib.Path(__file__).resolve().parent

# ---- encounter geometry (all vectors 3-D, sec. II-C) ------------------------
V_I = np.array([40.0, 0.0, 0.0])          # i: 40 m/s east
V_J = np.array([0.0, 30.0, 0.0])          # j: 30 m/s north
ALT = 200.0                               # both at the same altitude [m]
P_I0 = np.array([0.0, 0.0, ALT])
P_J0 = np.array([1615.0, -1180.0, ALT])   # -> r(40 s) = (15, 20, 0), |r| = 25 m
T_CPA = 40.0                              # instant of closest approach [s]
WINDOW = 60.0                             # plotted / counted window [s]


def beacon_instants(t, interval, t_last=None):
    """Algorithm 1 scheduler: broadcast whenever ``t - t_last >= T_i(t)``."""
    t_last = t[0] if t_last is None else t_last
    out = []
    for tk, T in zip(t, interval):
        if tk - t_last >= T - 1e-9:
            out.append(tk)
            t_last = tk
    return np.asarray(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE / "results" / "fig2_crossing_encounter.png"))
    a = ap.parse_args()

    cfg = Config()
    t = np.arange(0.0, WINDOW + 1e-9, cfg.dt)

    # ---- true geometry and risk seen by i
    p_i = P_I0 + np.outer(t, V_I)
    p_j = P_J0 + np.outer(t, V_J)
    v_i = np.broadcast_to(V_I, p_i.shape)
    v_j = np.broadcast_to(V_J, p_j.shape)
    tcpa, dcpa = pairwise_geometry(p_i, v_i, p_j, v_j)
    risk = conflict_risk(dcpa, tcpa, cfg.d0, cfg.tau0)

    # ---- risk-to-interval mapping (8) and the beacon scheduler
    interval = risk_to_interval(risk, cfg.T_min, cfg.T_max)
    # i is already beaconing when the window opens, so it transmits at t = 0
    beams = beacon_instants(t, interval, t_last=-np.inf)

    below1 = t[np.argmax(interval < 1.0)]
    n_prop = int((beams < WINDOW).sum())
    print(f"interval < 1 s from t = {below1:.2f} s")
    print(f"interval just before the CPA: {interval[np.argmin(np.abs(t - T_CPA + cfg.dt))]:.2f} s "
          f"(minimum {interval.min():.2f} s at t = {t[np.argmin(interval)]:.2f} s)")
    print(f"beacons of eVTOL i in [0, {WINDOW:.0f}) s : {n_prop} "
          f"(Fixed-High {int(round(WINDOW / cfg.T_min))}, "
          f"Fixed-Low {int(round(WINDOW / cfg.T_max))})")
    print(f"risk at t = 0: {risk[0]:.4f};  peak risk: {risk.max():.4f} at t = {t[np.argmax(risk)]:.2f} s")

    # ------------------------------------------------------------------ figure
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(6.3, 4.7), sharex=True,
        gridspec_kw=dict(height_ratios=[1.05, 1.0], hspace=0.12))

    # (a) risk
    ax1.plot(t, risk, color="#1F5FBF", lw=2.6)
    ax1.axvline(T_CPA, color="0.25", lw=1.0, ls=":")
    ax1.annotate(r"CPA ($D_{\mathrm{CPA}} = 25$ m)", xy=(T_CPA + 1.5, 0.93),
                 ha="left", va="top", fontsize=10.5, color="0.25")
    ax1.annotate(r"$T_{\mathrm{CPA}} = 15$ s", xy=(25.0, risk[np.argmin(np.abs(t - 25.0))]),
                 xytext=(11.5, 0.60), fontsize=11,
                 arrowprops=dict(arrowstyle="-", color="0.35", lw=0.9,
                                 shrinkA=0, shrinkB=2))
    ax1.set_ylabel(r"Risk $R_i$")
    ax1.set_ylim(-0.03, 1.0)
    ax1.set_yticks([0.0, 0.5, 1.0])
    tidy(ax1)

    # (b) beacon interval
    ax2.plot(t, interval, color="#1F5FBF", lw=2.6, label=r"$T_i$ (proposed)")
    ax2.axhline(cfg.T_max, color="#14A085", lw=2.0, ls="-.",
                dashes=(6, 2, 1, 2), label="Fixed-Low")
    ax2.axhline(cfg.T_min, color="#E4703A", lw=2.0, ls="--", label="Fixed-High")
    ax2.axvline(T_CPA, color="0.25", lw=1.0, ls=":")

    # transmission instants, drawn as tick marks above the axes
    y0, y1 = 2.05, 2.24
    ax2.vlines(beams, y0, y1, color="0.15", lw=1.0)
    ax2.text(0.4, 2.32, "beacon instants of eVTOL $i$", fontsize=10, color="0.3",
             ha="left", va="bottom")

    ax2.set_ylabel(r"Interval $T_i$ [s]")
    ax2.set_xlabel("Time [s]")
    ax2.set_xlim(0, WINDOW)
    ax2.set_ylim(0, 2.55)
    ax2.set_yticks([0, 1, 2])
    ax2.set_yticks([0.1, 1.0, 2.0], minor=True)
    ax2.legend(loc="center right", frameon=False, handlelength=2.4,
               borderaxespad=0.6)
    tidy(ax2)

    for ax in (ax1, ax2):
        ax.set_xticks([0, 10, 20, 30, 40, 50, 60])

    fig.align_ylabels([ax1, ax2])
    fig.savefig(a.out)
    print(f"written {a.out}")


if __name__ == "__main__":
    main()
