# From the paper to the code (reading guide)

This file is the bridge between the manuscript and the programs: for every
element of the paper it says what is claimed, where the claim is implemented,
which script produces the corresponding artefact, and what a reader should
expect to see.

## What the paper does in ten lines

1. **Problem** — eVTOL air taxis in low-altitude urban corridors must know each
   other's state.  Direct V2V beacons provide it, but a fixed beacon period is a
   bad compromise: 10 Hz congests the channel (the packet delivery ratio
   collapses), 0.5 Hz leaves neighbour information stale exactly when an
   encounter develops.
2. **Idea** — let every aircraft predict, from the beacons it already receives,
   *where and when* it would come closest to each neighbour (DCPA, TCPA), turn
   the most critical pair into a normalised risk `R_i`, and make the beacon
   interval a linear function of that risk between 0.1 s and 2 s.
3. **Model** — 2 km × 2 km sector, 3 + 3 bidirectional corridors, 10–50
   aircraft at 20–50 m/s in 100–300 m altitude, unslotted (pure ALOHA) channel
   with 1000 m range, 200 B beacons and 1 Mb/s.
4. **Evaluation** — a fully vectorised NumPy simulator, 50 Monte Carlo runs per
   configuration, four schemes: proposed, Fixed-High (0.1 s), Fixed-Low (2 s),
   and a rate-matched fixed schedule (same number of messages as the proposed
   rule, but sent periodically).
5. **Result** — 90.8–93.5 % fewer beacons than 10 Hz while keeping the PDR near
   0.91, and, at an equal message budget, 12–29 % fresher information and
   27–50 % lower tail position error in critical encounters.  The gain comes
   from *when* the messages are sent, not how many.

## Paper element → code → artefact

| Paper element | What it claims | Implementation | Produced by | Artefact |
|---|---|---|---|---|
| Sec. II-A, Fig. 1(a), Table I | corridor mobility, lane keeping, bank-limited turns, random speed/altitude targets, new entrants | `v2vbeacon/mobility.py` | `fig1_system_overview.py` (drawing only) | `results/fig1_system_overview.png` |
| Sec. II-B, eq. (1)–(2) | beacon content, dead reckoning, age of information | `engine.simulate` (neighbour table) | — | — |
| Sec. II-B | pure ALOHA: range, overlap in time, half duplex, residual loss | `engine.simulate` (channel block) | `fig3_channel_load.py` (panel b) | `results/fig3_channel_load.png` |
| Sec. II-C, eq. (3)–(4) | TCPA / DCPA in 3-D | `geometry.pairwise_geometry` | `fig2_crossing_encounter.py`, all metrics | — |
| Sec. III-A, eq. (5)–(7) | distance factor, time factor, pairwise risk, `R_i = max_j R_ij` | `geometry.conflict_risk` | `fig2_crossing_encounter.py` (top panel) | `results/fig2_crossing_encounter.png` |
| Sec. III-B, eq. (8) | `T_i = T_max − R_i (T_max − T_min)` | `geometry.risk_to_interval` | `fig2` (bottom panel), `fig3`, `fig4` | — |
| Algorithm 1 | update table → compute risk → broadcast if `t − t_last ≥ T_i` | `engine.simulate` (beacon decision) | `fig2` (beacon tick marks) | — |
| Sec. IV, Table I | parameters, metrics, Monte Carlo protocol, common random numbers | `v2vbeacon/config.py`, `engine.py` | `run_sweep.py` | `results/sweep.csv` |
| Sec. IV, baselines | Fixed-High, Fixed-Low, rate-matched (period = 1/rate of the proposed scheme in the same run) | `engine.simulate(scheme=...)`, `sweep.run_sweep` | `fig3`, `fig4`, `table2` | — |
| Sec. V-A, Fig. 3 | beacon load and PDR versus N | metrics `rate`, `pdr` | `fig3_channel_load.py` | `results/fig3_channel_load.png` |
| Sec. V-B, Fig. 4(a,b) | age of information and P95 dead-reckoning error in critical pairs | metrics `age_mean`, `err_p95`, `stale` | `fig4_timeliness.py` | `results/fig4_timeliness.png` |
| Sec. V-C, eq. (9), Fig. 4(c) | conflict-detection delay | metric `delay_mean`, `delay_p95`, `miss` | `fig4_timeliness.py` | same figure |
| Sec. V, Table II | one row per scheme at N = 50 | all of the above | `table2_main_results.py` | `results/table2_main_results.md` |
| Sec. V-D, Table III | sensitivity to the risk scales `D0`, `T0` | `Config.with_(d0=..., tau0=...)` | `table3_risk_scales.py` | `results/table3_risk_scales.md` |

## Suggested reading order for the code

1. `v2vbeacon/config.py` — the whole of Table I in one dataclass, with the
   every airspace parameter of Table I in one place.
2. `v2vbeacon/geometry.py` — eqs. (3)–(8) in ~60 lines.
3. `v2vbeacon/mobility.py` — the traffic of Sec. II-A (one flight-dynamics step
   per call, vectorised over Monte Carlo runs).
4. `v2vbeacon/engine.py` — the main loop: beacon decision → channel → neighbour
   table → metrics; docstrings point at the equation of every block.
5. `fig2_crossing_encounter.py` — the smallest end-to-end example of the
   mechanism (analytic, no Monte Carlo).
6. `fig3_channel_load.py`, `fig4_timeliness.py` — plotting only.
7. `table2_main_results.py`, `table3_risk_scales.py`.

## Conventions used everywhere

* Shapes: the leading axis of every array is the **Monte Carlo run**; the
  second is the **aircraft index**; pairwise quantities have two aircraft axes
  `[run, i, j]`; the last axis of a vector array is the 3-D vector.
* Units: metres, seconds, m/s, m/s², radians internally; degrees only in
  `Config` (`phi_max`).
* Two random generators: `seed` for mobility, `seed + 7919` for the channel, so
  that all schemes see identical traffic (common random numbers, Sec. IV).
* `results/sweep.csv` is the single source of the density sweep; Figs. 3–4 and
  Table II all read it, so they cannot contradict each other.
