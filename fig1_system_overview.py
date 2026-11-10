"""FIGURE 1 - System overview (corridor grid + on-board chain).

WHAT THE PAPER CLAIMS
---------------------
Panel (a): eVTOL air taxis share a 2 km x 2 km grid of bidirectional urban air
corridors (three east-west and three north-south corridors, 600 m apart, one
lane per direction offset 25 m to the right of the centre-line) and broadcast
V2V beacons M_i = {ID_i, p_i, v_i, t_i}.  A pair converging on an intersection
(orange) predicts a small DCPA within a short TCPA and therefore beacons
rapidly (T_i -> T_min = 0.1 s), while well separated aircraft (blue) beacon
slowly (T_i -> T_max = 2 s).  Panel (a) is a top view only: every conflict
computation uses the full 3-D position and velocity.
Panel (b): the processing chain executed by every eVTOL - receive beacons,
dead-reckon the neighbour table, compute the encounter geometry, turn it into a
conflict risk, map the risk onto a beacon interval, schedule the next
broadcast.  The shaded blocks are the proposed mechanism (Sec. III-A/III-B).

WHERE IN THE PAPER
------------------
Fig. 1, Sec. I (contributions), Sec. II (system model), Sec. III (mechanism),
Algorithm 1.

HOW TO READ THIS PROGRAM
------------------------
1. `panel_a()` draws the airspace of Sec. II-A plus the two risk regimes of
   Sec. III-B.  It is pure drawing: no simulation is run.
2. `panel_b()` draws the chain of Sec. II-C / Sec. III and marks the three
   proposed blocks with the orange bracket.
3. `evtol()` is the aircraft icon, `box()` one rounded box of panel (b).
Every number that appears in the figure (600 m spacing, 25 m lanes, 100-300 m,
0.1 s / 2 s) is read from `v2vbeacon.Config`, i.e. from Table I - nothing is
hard-wired twice.

INPUT / OUTPUT
--------------
No input, no randomness.  Writes results/fig1_system_overview.png.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from v2vbeacon import Config
from v2vbeacon.style import plt

HERE = pathlib.Path(__file__).resolve().parent

BLUE = "#1F6FD0"
ORANGE = "#E4703A"
ORANGE_L = "#F6D9C9"
BLUE_L = "#DCE9F8"
GREY = "#EAEAEA"
DASH = "#B9B9B9"


# ---------------------------------------------------------------- eVTOL symbol
def evtol(ax, x, y, colour, s=2.6):
    """Draw a top-view eVTOL icon (four rotors on a lifting body)."""
    ax.add_patch(Ellipse((x, y), 26 * s, 9.5 * s, facecolor=colour,
                         edgecolor=colour, lw=0.8, zorder=6))
    for dx in (-15, 15):
        for dy in (-8, 8):
            ax.add_patch(Circle((x + dx * s, y + dy * s), 6.2 * s, facecolor="white",
                                edgecolor=colour, lw=1.3, zorder=7))
            ax.plot([x + dx * 0.3 * s, x + dx * 0.85 * s],
                    [y + dy * 0.12 * s, y + dy * 0.7 * s],
                    color=colour, lw=1.3, zorder=6, solid_capstyle="round")


# ------------------------------------------------------------------- panel (a)
def panel_a(ax, cfg: Config):
    half = cfg.sector / 2.0
    ax.set_xlim(-half, half)
    ax.set_ylim(-half, half)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("0.55")

    # background sector
    ax.add_patch(Rectangle((-half, -half), cfg.sector, cfg.sector,
                           facecolor="#FAFAFA", edgecolor="0.55", lw=0.9, zorder=0))

    # corridors: one lane per direction, 25 m right of the centre-line
    for c in cfg.corridors:
        ax.add_patch(Rectangle((-half, c - 45), cfg.sector, 90,
                               facecolor=GREY, edgecolor="none", zorder=1))
        ax.add_patch(Rectangle((c - 45, -half), 90, cfg.sector,
                               facecolor=GREY, edgecolor="none", zorder=1))
    # lane centre-lines (one lane per direction, 25 m right of the centre-line)
    for c in cfg.corridors:
        for lane in (c - cfg.lane_offset, c + cfg.lane_offset):
            ax.plot([-half, half], [lane, lane], ls=(0, (6, 4)), color=DASH, lw=1.0, zorder=2)
            ax.plot([lane, lane], [-half, half], ls=(0, (6, 4)), color=DASH, lw=1.0, zorder=2)

    # the converging pair
    p_i = (-330.0, -85.0)
    p_j = (-55.0, -345.0)
    cpa = (25.0, -30.0)

    for p in (p_i, p_j):
        ax.add_patch(Circle(p, 115, facecolor=ORANGE_L, edgecolor=ORANGE,
                            lw=1.2, alpha=0.85, zorder=3))
    ax.add_patch(Circle(p_i, 168, facecolor="none", edgecolor=ORANGE, lw=0.9,
                        alpha=0.6, zorder=3))
    ax.add_patch(Circle(p_j, 168, facecolor="none", edgecolor=ORANGE, lw=0.9,
                        alpha=0.6, zorder=3))

    # predicted closest approach
    ax.plot(*cpa, marker="x", ms=9, mew=2.0, color=ORANGE, zorder=8)
    ax.annotate("", xy=(cpa[0] - 12, cpa[1]), xytext=(p_i[0] + 40, p_i[1]),
                arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=1.4,
                                ls=(0, (4, 3)), shrinkA=0, shrinkB=2), zorder=5)
    ax.plot([cpa[0], p_j[0]], [cpa[1], p_j[1]], ls=(0, (4, 3)), color=ORANGE,
            lw=1.4, zorder=5)

    # aircraft
    for x, y in ((-780, 700), (-215, 845), (395, 865), (665, 600),
                 (-700, -805), (520, -890)):
        evtol(ax, x, y, BLUE)
    evtol(ax, *p_i, ORANGE)
    evtol(ax, *p_j, ORANGE)

    # a predicted path of the crossing traffic
    ax.plot([665, cpa[0]], [600, cpa[1]], ls=(0, (2, 3)), color="0.45", lw=1.1, zorder=4)

    # beacon message box
    ax.annotate("V2V beacon  $M_i=\\{ID_i,\\ \\mathbf{p}_i,\\ \\mathbf{v}_i,\\ t_i\\}$",
                xy=(-905, 940), fontsize=10.5,
                ha="left", va="center",
                bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                          edgecolor="0.45", lw=0.9), zorder=9)

    # annotations
    ax.text(cpa[0] + 120, cpa[1] + 120, "predicted CPA,\n$T_{\\mathrm{CPA}}$ ahead",
            color=ORANGE, fontsize=10.5, ha="left", va="bottom")
    ax.text(cpa[0] - 150, cpa[1] + 60, "$D_{\\mathrm{CPA}}$", color="0.2",
            fontsize=11.5, ha="right", va="bottom")
    ax.text(p_i[0] - 40, p_i[1] - 175, "eVTOL $i$", fontsize=11.5, ha="center",
            va="top", color="0.1")
    ax.text(p_j[0] + 175, p_j[1] + 20, "eVTOL $j$", fontsize=11.5, ha="left",
            va="center", color="0.1")
    ax.text(700, 760, "low risk:\n$T_i \\rightarrow T_{\\max} = 2$ s", color=BLUE,
            fontsize=10.5, ha="center", va="bottom")
    ax.text(p_i[0] - 215, p_i[1] - 340, "high risk:\n$T_i \\rightarrow T_{\\min} = 0.1$ s",
            color=ORANGE, fontsize=10.5, ha="center", va="top")

    ax.set_title("Urban air-corridor grid (top view, 2 km $\\times$ 2 km, "
                 "100–300 m AGL)", fontsize=11.5, pad=8)
    ax.text(0.5, -0.055, "(a)", transform=ax.transAxes, ha="center", va="top",
            fontsize=12)


# ------------------------------------------------------------------- panel (b)
def box(ax, y0, h, title, body, colour, x0=0.055, x1=0.90):
    """One processing-chain box (title + formula)."""
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, h,
                                boxstyle="round,pad=0.004,rounding_size=0.012",
                                facecolor=colour, edgecolor="0.45", lw=0.9,
                                zorder=2))
    ax.text(x0 + 0.024, y0 + h * 0.70, title, fontsize=11.5, fontweight="bold",
            va="center", ha="left", zorder=3)
    ax.text(x0 + 0.024, y0 + h * 0.30, body, fontsize=11.0, va="center",
            ha="left", zorder=3)


def panel_b(ax, cfg: Config):
    ax.set_xlim(0, 1.16)
    ax.set_ylim(-0.02, 1)
    ax.axis("off")

    h = 0.125
    ys = [0.855, 0.685, 0.515, 0.345, 0.175, 0.005]
    specs = [
        ("V2V receiver", "beacons $M_j$ from in-range neighbours $j$", BLUE_L),
        ("Neighbour table",
         "dead reckoning:  $\\hat{\\mathbf{p}}_j=\\mathbf{p}_j(t_k)+"
         "\\mathbf{v}_j(t_k)\\,(t-t_k)$", BLUE_L),
        ("Conflict geometry",
         "$\\mathbf{r}_{ij},\\ \\mathbf{v}_{ij}\\ \\rightarrow\\ "
         "T_{\\mathrm{CPA}},\\ D_{\\mathrm{CPA}}$", ORANGE_L),
        ("Conflict risk",
         "$R_{ij}=e^{-D_{\\mathrm{CPA}}/D_0}\\,e^{-T_{\\mathrm{CPA}}/T_0}$,   "
         "$R_i=\\max_j R_{ij}$", ORANGE_L),
        ("Beacon interval",
         "$T_i=T_{\\max}-R_i\\,(T_{\\max}-T_{\\min})$", ORANGE_L),
        ("Beacon scheduler",
         "broadcast $M_i$ when $t-t_i^{\\mathrm{last}}\\geq T_i$", BLUE_L),
    ]
    for (title, body, colour), y in zip(specs, ys):
        box(ax, y, h, title, body, colour)

    # arrows between the boxes
    for y_top, y_bot in zip(ys[:-1], ys[1:]):
        ax.add_patch(FancyArrowPatch((0.48, y_top - 0.002), (0.48, y_bot + h + 0.004),
                                     arrowstyle="-|>", mutation_scale=13,
                                     color="0.35", lw=1.1, zorder=4))

    # own state input
    ax.add_patch(FancyArrowPatch((1.115, ys[2] + h / 2), (0.905, ys[2] + h / 2),
                                 arrowstyle="-|>", mutation_scale=13,
                                 color="0.35", lw=1.1))
    ax.text(1.125, ys[2] + h / 2, "own\n$\\mathbf{p}_i,\\mathbf{v}_i$\n(GNSS/\nINS)",
            fontsize=9.5, ha="left", va="center", linespacing=0.95)

    # V2V transmit output
    ax.add_patch(FancyArrowPatch((0.90, ys[5] + h / 2), (1.06, ys[5] + h / 2),
                                 arrowstyle="-|>", mutation_scale=13,
                                 color="0.35", lw=1.1))
    ax.text(1.075, ys[5] + h / 2, "V2V\ntx", fontsize=9.5, ha="left", va="center",
            linespacing=0.95)

    # bracket marking the proposed mechanism
    yb_hi, yb_lo = ys[4] + h - 0.004, ys[2] + 0.004
    xb = 0.036
    ax.plot([xb, xb], [yb_lo, yb_hi], color=ORANGE, lw=2.6, solid_capstyle="butt")
    ax.plot([xb, xb + 0.014], [yb_hi, yb_hi], color=ORANGE, lw=2.6)
    ax.plot([xb, xb + 0.014], [yb_lo, yb_lo], color=ORANGE, lw=2.6)
    ax.text(xb - 0.012, 0.5 * (yb_lo + yb_hi), "proposed", rotation=90,
            ha="center", va="center", fontsize=11, color=ORANGE)

    ax.set_title("On-board conflict-risk-aware beaconing (every eVTOL $i$)",
                 fontsize=11.5, pad=8)
    ax.text(0.5, -0.06, "(b)", transform=ax.transAxes, ha="center", va="top",
            fontsize=12)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(HERE / "results" / "fig1_system_overview.png"))
    a = ap.parse_args()

    cfg = Config()
    fig = plt.figure(figsize=(13.6, 6.2))
    ax_a = fig.add_axes([0.03, 0.08, 0.42, 0.80])
    ax_b = fig.add_axes([0.51, 0.06, 0.46, 0.84])

    panel_a(ax_a, cfg)
    panel_b(ax_b, cfg)
    fig.savefig(a.out)
    print(f"written {a.out}")


if __name__ == "__main__":
    main()
