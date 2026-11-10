"""eVTOL corridor mobility (Sec. II-A).

The airspace is the 2 km x 2 km sector of Fig. 1 with three east-west and three
north-south corridors spaced 600 m apart.  Every corridor carries one lane per
direction, offset 25 m to the right of the centre-line.  Each aircraft tracks
its lane with a line-of-sight guidance law

        psi_des = psi_lane + sign * atan(e_ct / L_look)

(e_ct = cross-track error, L_look = look-ahead distance), whose heading rate is
limited by the maximum bank angle,

        |omega| <= g tan(phi_max) / |v|,

turns onto the crossing corridor at an intersection with probability p_turn,
and randomly re-draws its target airspeed in 20-50 m/s (acceleration limited)
and its target altitude in 100-300 m (climb-rate limited).  Aircraft that leave
the sector are replaced by new entrants, so that N stays constant.

The whole state is vectorised over Monte Carlo runs; the leading axis of every
array is the run index.  The random-number generator of this class is distinct
from the one used by the channel, which implements the common-random-numbers
requirement of Sec. IV.
"""

from __future__ import annotations

import numpy as np

from .config import Config


class Mobility:
    """Vectorised corridor mobility of ``n`` eVTOLs over ``n_runs`` runs."""

    #: axis index conventions: 0 = east-west corridor, 1 = north-south corridor
    EW, NS = 0, 1

    def __init__(self, cfg: Config, n: int, n_runs: int, seed: int):
        self.cfg = cfg
        self.n = n
        self.nr = n_runs
        self.rng = np.random.default_rng(seed)
        self.offs = np.asarray(cfg.corridors, dtype=float)

        rng = self.rng
        shape = (n_runs, n)
        self.axis = rng.integers(0, 2, size=shape)                       # corridor orientation
        self.dirn = rng.choice(np.array([-1.0, 1.0]), size=shape)        # travelling direction
        self.corr = rng.choice(self.offs, size=shape)                    # corridor centre coordinate

        self.pos = np.zeros(shape + (3,))
        self.vel = np.zeros(shape + (3,))
        self.heading = np.zeros(shape)
        self.speed = np.zeros(shape)
        self.v_target = np.zeros(shape)
        self.vz = np.zeros(shape)
        self.alt_target = np.zeros(shape)

        self._place(np.ones(shape, dtype=bool), boundary=False)
        self.prev_along = self._along()
        self.decided = np.full(shape, np.inf)   # last intersection with a decision
        self.cooldown = np.zeros(shape)
        self.respawned = np.zeros(shape, dtype=bool)

    # ------------------------------------------------------------------ helpers
    def _along(self) -> np.ndarray:
        """Along-corridor coordinate of every aircraft [m]."""
        return np.where(self.axis == self.EW, self.pos[..., 0], self.pos[..., 1])

    def _sync_vel(self) -> None:
        """Recompute the velocity vector from (speed, heading, climb rate)."""
        self.vel[..., 0] = self.speed * np.cos(self.heading)
        self.vel[..., 1] = self.speed * np.sin(self.heading)
        self.vel[..., 2] = self.vz

    def _place(self, mask: np.ndarray, boundary: bool) -> None:
        """Place the selected aircraft on their lane, with a fresh speed/altitude.

        ``boundary=True`` puts them on the sector boundary at which they enter,
        ``boundary=False`` puts them at a uniformly random point of the lane.
        """
        cfg = self.cfg
        rng = self.rng
        m = int(np.count_nonzero(mask))
        if m == 0:
            return

        half = 0.5 * cfg.sector
        ax = self.axis[mask]
        d = self.dirn[mask]
        c = self.corr[mask]
        lane = np.where(ax == self.EW,
                        c - cfg.lane_offset * d,      # east-west lane (lateral = y)
                        c + cfg.lane_offset * d)      # north-south lane (lateral = x)
        if boundary:
            along = -d * half                          # enter at the upstream boundary
        else:
            along = rng.uniform(-half, half, size=m)

        self.pos[mask, 0] = np.where(ax == self.EW, along, lane)
        self.pos[mask, 1] = np.where(ax == self.EW, lane, along)
        self.pos[mask, 2] = rng.uniform(cfg.alt_min, cfg.alt_max, size=m)

        self.speed[mask] = rng.uniform(cfg.v_min, cfg.v_max, size=m)
        self.v_target[mask] = self.speed[mask]
        self.alt_target[mask] = rng.uniform(cfg.alt_min, cfg.alt_max, size=m)
        self.vz[mask] = 0.0

        hd = np.where(ax == self.EW,
                      np.where(d > 0, 0.0, np.pi),
                      np.where(d > 0, 0.5 * np.pi, -0.5 * np.pi))
        self.heading[mask] = hd
        self._sync_vel()

    # -------------------------------------------------------------------- update
    def step(self, t: float) -> None:
        """Advance every aircraft by one control step ``cfg.dt``."""
        cfg = self.cfg
        rng = self.rng
        shape = (self.nr, self.n)
        dt = cfg.dt

        # ---- 1. random re-draw of the targets (Poisson event, sec. II-A)
        ev = rng.random(shape) < cfg.speed_change_rate * dt
        if ev.any():
            self.v_target[ev] = rng.uniform(cfg.v_min, cfg.v_max, int(ev.sum()))
        ev = rng.random(shape) < cfg.alt_change_rate * dt
        if ev.any():
            self.alt_target[ev] = rng.uniform(cfg.alt_min, cfg.alt_max, int(ev.sum()))

        # ---- 2. look-ahead guidance law, heading rate limited by the bank angle
        # cross-track error of the lane (positive = lane lies to the "north/east")
        ew = self.axis == self.EW
        e_ct = np.where(ew,
                        (self.corr - cfg.lane_offset * self.dirn) - self.pos[..., 1],
                        (self.corr + cfg.lane_offset * self.dirn) - self.pos[..., 0])
        # line-of-sight heading: forward direction plus a bounded cross-track correction
        ang = np.arctan2(e_ct, cfg.lookahead)
        sign = np.where(ew, self.dirn, -self.dirn)
        fwd = np.where(ew,
                       np.where(self.dirn > 0, 0.0, np.pi),
                       np.where(self.dirn > 0, 0.5 * np.pi, -0.5 * np.pi))
        desired = fwd + sign * ang
        err = np.arctan2(np.sin(desired - self.heading), np.cos(desired - self.heading))
        omega_lim = cfg.omega_max / np.maximum(self.speed, 1.0)
        self.heading += np.clip(err, -omega_lim * dt, omega_lim * dt)

        # ---- 3. speed / climb-rate limited integration
        self.speed += np.clip(self.v_target - self.speed, -cfg.a_max * dt, cfg.a_max * dt)
        vz_target = np.clip((self.alt_target - self.pos[..., 2]) * 0.5, -cfg.vz_max, cfg.vz_max)
        self.vz += np.clip(vz_target - self.vz, -cfg.a_z_max * dt, cfg.a_z_max * dt)

        self.pos[..., 0] += self.speed * np.cos(self.heading) * dt
        self.pos[..., 1] += self.speed * np.sin(self.heading) * dt
        self.pos[..., 2] += self.vz * dt
        self._sync_vel()

        # ---- 4. intersection decisions
        self._intersections(t)
        # ---- 5. replacement of aircraft that left the sector
        half = 0.5 * cfg.sector + cfg.respawn_margin
        out = (np.abs(self.pos[..., 0]) > half) | (np.abs(self.pos[..., 1]) > half)
        self.respawned = out
        if out.any():
            self.axis[out] = rng.integers(0, 2, int(out.sum()))
            self.dirn[out] = rng.choice(np.array([-1.0, 1.0]), int(out.sum()))
            self.corr[out] = rng.choice(self.offs, int(out.sum()))
            self._place(out, boundary=True)
            self.cooldown[out] = 0.0
            self.decided[out] = np.inf
            self.prev_along = np.where(out, self._along(), self.prev_along)

    def _intersections(self, t: float) -> None:
        """Turn onto the crossing corridor with probability ``p_turn``.

        The decision is taken one turn radius before the intersection, so that
        the aircraft flies a fillet turn and re-acquires the new lane without a
        large overshoot - the heading rate is limited by the bank angle, hence
        the turn radius is R = v / omega_max = v^2 / (g tan phi_max).
        """
        cfg = self.cfg
        rng = self.rng

        along = self._along()
        dist = (self.offs[None, None, :] - along[..., None]) * self.dirn[..., None]
        dist = np.where(dist > 0.0, dist, np.inf)            # next intersection ahead
        k_next = np.argmin(dist, axis=2)
        d_next = np.take_along_axis(dist, k_next[..., None], axis=2)[..., 0]
        off_next = self.offs[k_next]

        radius = self.speed ** 2 / cfg.omega_max             # turn radius [m]
        due = (d_next <= np.maximum(radius, cfg.lookahead)) \
            & (np.abs(off_next - self.decided) > 1e-6) & (t >= self.cooldown)
        if not due.any():
            return

        self.decided = np.where(due, off_next, self.decided)
        turn = due & (rng.random(due.shape) < cfg.p_turn)
        if turn.any():
            k = int(turn.sum())
            old_corr = self.corr[turn]                  # crossing corridor just used
            self.axis[turn] = 1 - self.axis[turn]
            self.dirn[turn] = rng.choice(np.array([-1.0, 1.0]), k)
            self.corr[turn] = off_next[turn]
            self.cooldown[turn] = t + cfg.turn_cooldown
            # the intersection that was just used is an intersection of the new
            # axis as well - no second decision there (that would be a U-turn
            # back onto the corridor that was just left)
            self.decided[turn] = old_corr
        self.prev_along = self._along()
