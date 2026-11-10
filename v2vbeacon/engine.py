"""Discrete-time Monte-Carlo engine (Sec. II-IV).

One call of :func:`simulate` runs one configuration (traffic density, beaconing
scheme) for ``n_runs`` Monte Carlo repetitions.  Every repetition is vectorised:
the leading axis of every state array is the run index.  Mobility randomness
(``rng_mobility``) and channel randomness (``rng_channel``) come from two
separate seeded generators, so that all schemes experience identical traffic
and identical channel realisations (common random numbers, Sec. IV).

Schemes
-------
``fixed_high``    periodic, T = T_min = 0.1 s          (Fixed-High)
``fixed_low``     periodic, T = T_max = 2 s            (Fixed-Low)
``rate_matched``  periodic with T set to the inverse of the average rate that
                  the proposed scheme achieved in the *same* run (Fixed,
                  rate-matched)
``proposed``      conflict-risk-aware adaptive interval (8)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .config import Config
from .geometry import conflict_risk, pairwise_geometry, risk_to_interval
from .mobility import Mobility

SCHEMES = ("proposed", "fixed_high", "fixed_low", "rate_matched")

#: summary/plot label of every scheme
LABEL = {
    "fixed_high": "Fixed-High (0.1 s)",
    "proposed": "Proposed (adaptive)",
    "rate_matched": "Fixed, rate-matched",
    "fixed_low": "Fixed-Low (2 s)",
}

NEG = -1.0e9


# ----------------------------------------------------------------------------
@dataclass
class SimResult:
    """Per-run metrics of one configuration."""

    scheme: str
    n: int
    n_runs: int
    rate: np.ndarray            # beacons per second per aircraft
    pdr: np.ndarray             # packet delivery ratio
    age_mean: np.ndarray        # mean age of information in critical pairs [s]
    age_p95: np.ndarray         # 95th percentile of the same [s]
    err_mean: np.ndarray        # mean dead-reckoning error, critical pairs [m]
    err_p95: np.ndarray         # 95th percentile of the same [m]
    stale: np.ndarray           # share of stale critical samples
    delay_mean: np.ndarray      # mean conflict-detection delay [s]
    delay_p95: np.ndarray       # 95th percentile of the same [s]
    miss: np.ndarray            # share of missed critical encounters
    all_err_mean: np.ndarray    # mean dead-reckoning error, all in-range pairs [m]
    crit_per_veh: np.ndarray    # critical neighbours per aircraft

    # ---------------------------------------------------------------- summary
    def summary(self) -> dict:
        """Mean (+/- standard error) of every metric over the runs."""
        out = {}
        for k, v in self.__dict__.items():
            if isinstance(v, np.ndarray):
                v = np.asarray(v, dtype=float)
                out[k] = float(np.nanmean(v))
                out[k + "_se"] = float(np.nanstd(v, ddof=1) / np.sqrt(v.size)) if v.size > 1 else 0.0
        return out

    def row(self) -> dict:
        """The columns of Table II."""
        s = self.summary()
        return dict(
            scheme=self.scheme,
            n=self.n,
            rate=s["rate"],
            pdr=s["pdr"],
            age=s["age_mean"],
            err_p95=s["err_p95"],
            stale=s["stale"],
            delay_mean=s["delay_mean"],
            delay_p95=s["delay_p95"],
            miss=s["miss"],
            err_mean=s["err_mean"],
            all_err_mean=s["all_err_mean"],
            crit_per_veh=s["crit_per_veh"],
        )


# ----------------------------------------------------------------------------
def _group_append(index: np.ndarray, values: np.ndarray, buckets: list) -> None:
    """Append ``values`` to ``buckets[index]`` (used for per-run quantiles)."""
    order = np.argsort(index, kind="stable")
    idx = index[order]
    val = values[order]
    uniq, starts = np.unique(idx, return_index=True)
    for u, part in zip(uniq, np.split(val, starts[1:])):
        buckets[int(u)].append(part)


# ----------------------------------------------------------------------------
def simulate(
    cfg: Config,
    n: int,
    scheme: str,
    n_runs: Optional[int] = None,
    seed: Optional[int] = None,
    T_period: Optional[np.ndarray] = None,
    verbose: bool = False,
) -> SimResult:
    """Run one Monte-Carlo configuration.

    Parameters
    ----------
    cfg : Config
    n : int
        Number of eVTOLs.
    scheme : {'proposed', 'fixed_high', 'fixed_low', 'rate_matched'}
    n_runs : int, optional
        Overrides ``cfg.n_runs``.
    seed : int, optional
        Overrides ``cfg.seed``.
    T_period : ndarray, optional
        Per-run beacon period [s] used by the ``rate_matched`` scheme.
    """
    if scheme not in SCHEMES:
        raise ValueError(f"unknown scheme {scheme!r}")
    nr = int(cfg.n_runs if n_runs is None else n_runs)
    seed = int(cfg.seed if seed is None else seed)

    dt = cfg.dt
    n_steps = int(round(cfg.duration / dt))
    k_warm = int(round(cfg.warmup / dt))
    T_win = cfg.duration - cfg.warmup
    k_sample = max(1, int(round(0.1 / dt)))       # metrics sampled every 0.1 s

    if scheme == "rate_matched":
        if T_period is None:
            raise ValueError("rate_matched needs T_period (per-run period)")
        T_period = np.asarray(T_period, dtype=np.float64).reshape(-1)
        if T_period.size == 1:
            T_period = np.full(nr, float(T_period[0]))
    fixed_period = {"fixed_high": cfg.T_min, "fixed_low": cfg.T_max}.get(scheme)

    mob = Mobility(cfg, n, nr, seed)
    rng_ch = np.random.default_rng(seed + 7919)

    # ------------------------------------------------------------- neighbour tables
    t_rx = np.full((nr, n, n), NEG)          # [i, j]: time stamp of the last beacon
    p_rx = np.zeros((nr, n, n, 3))           # position carried by that beacon
    v_rx = np.zeros((nr, n, n, 3))           # velocity carried by that beacon

    # initial phase of the beacon schedule: t_last ~ U(-T, 0] so that the
    # transmissions of the population are not synchronised (pure ALOHA)
    T_phase = cfg.T_max if scheme == "proposed" else float(
        fixed_period if fixed_period is not None else np.max(T_period))
    t_tx = -rng_ch.random((nr, n)) * T_phase

    eye_idx = np.arange(n)

    # ---------------------------------------------------------------- accumulators
    tx_win = np.zeros(nr)
    att = np.zeros(nr)
    suc = np.zeros(nr)
    age_sum = np.zeros(nr)
    age_n = np.zeros(nr)
    err_sum = np.zeros(nr)
    err_n = np.zeros(nr)
    stale_sum = np.zeros(nr)
    crit_n = np.zeros(nr)
    all_err_sum = np.zeros(nr)
    all_err_n = np.zeros(nr)
    cpv_sum = np.zeros(nr)
    cpv_n = np.zeros(nr)
    det_cnt = np.zeros(nr)
    det_sum = np.zeros(nr)
    miss_cnt = np.zeros(nr)
    enc_cnt = np.zeros(nr)
    age_buckets = [[] for _ in range(nr)]
    err_buckets = [[] for _ in range(nr)]
    delay_buckets = [[] for _ in range(nr)]

    # ------------------------------------------------- encounter (delay) bookkeeping
    active = np.zeros((nr, n, n), dtype=bool)
    start = np.zeros((nr, n, n))
    det = np.full((nr, n, n), np.nan)

    pos = mob.pos
    vel = mob.vel

    for k in range(n_steps):
        t = k * dt

        if k > 0:
            mob.step(t)
            pos, vel = mob.pos, mob.vel
            rp = mob.respawned
            if rp.any():
                mi = np.broadcast_to(rp[:, :, None], (nr, n, n))
                mj = np.broadcast_to(rp[:, None, :], (nr, n, n))
                t_rx[mi] = NEG
                t_rx[mj] = NEG
                p_rx[mi] = 0.0
                p_rx[mj] = 0.0
                v_rx[mi] = 0.0
                v_rx[mj] = 0.0

        # ------------------------------------------------- dead-reckoned neighbour state (2)
        age_pre = t - t_rx
        has_pre = age_pre < 1.0e7
        age_pre_c = np.clip(age_pre, 0.0, None)
        p_hat = p_rx + v_rx * age_pre_c[..., None]

        # ------------------------------------------------------------ beacon decision
        if scheme == "proposed":
            tc_e, dc_e = pairwise_geometry(pos[:, :, None, :], vel[:, :, None, :], p_hat, v_rx)
            ok = has_pre & (age_pre_c <= cfg.T_timeout)        # neighbour set N_i
            risk = np.where(ok & (tc_e >= 0.0),
                            conflict_risk(dc_e, tc_e, cfg.d0, cfg.tau0), 0.0)
            risk[:, eye_idx, eye_idx] = 0.0
            T_i = risk_to_interval(risk.max(axis=2), cfg.T_min, cfg.T_max)
        elif fixed_period is not None:
            T_i = np.full((nr, n), float(fixed_period))
        else:                                    # rate-matched
            T_i = np.broadcast_to(T_period[:, None], (nr, n))

        tx = (t - t_tx) >= (T_i - 1e-9)
        t_tx = np.where(tx, t, t_tx)

        # ------------------------------------------------------------------- channel
        # two independent random draws per step: emission instant inside the step
        # (continuous-time scheduling) and residual loss
        off = rng_ch.random((nr, n)) * dt
        u_loss = rng_ch.random((nr, n, n))

        diff = pos[:, :, None, :] - pos[:, None, :, :]
        d2 = np.einsum("...k,...k->...", diff, diff)
        near = d2 <= cfg.R_comm ** 2                     # [i, j]: j is in range of i
        near[:, eye_idx, eye_idx] = False

        tdiff = np.abs(off[:, :, None] - off[:, None, :])
        overlap = (tdiff < cfg.airtime) & tx[:, :, None] & tx[:, None, :]
        overlap[:, eye_idx, eye_idx] = False
        collided = (overlap.astype(np.float32) @ near.astype(np.float32)) > 0.5

        # a beacon is "attempted" at every in-range receiver that is not itself
        # transmitting at the same instant (half duplex, condition (iii))
        attempts = tx[:, :, None] & near & ~overlap
        rx = attempts & ~collided & (u_loss > cfg.p_residual)

        if k >= k_warm:
            tx_win += tx.sum(axis=1)
            att += attempts.sum(axis=(1, 2))
            suc += rx.sum(axis=(1, 2))

        # -------------------------------------------------- update the neighbour table
        t_rx = np.where(rx, t, t_rx)
        p_rx = np.where(rx[..., None], pos[:, None, :, :], p_rx)
        v_rx = np.where(rx[..., None], vel[:, None, :, :], v_rx)

        # ----------------------------------------- true and perceived conflict geometry
        tc, dc = pairwise_geometry(pos[:, :, None, :], vel[:, :, None, :],
                                   pos[:, None, :, :], vel[:, None, :, :])
        crit = (dc <= cfg.d_crit) & (tc >= 0.0) & (tc <= cfg.t_crit) & near

        age = t - t_rx
        has = age < 1.0e7
        age_c = np.clip(age, 0.0, None)
        p_hat_new = p_rx + v_rx * age_c[..., None]

        # ------------------------------------------------- conflict-detection delay (9)
        if k >= k_warm:
            ended = active & ~crit
            if ended.any():
                ri, ii, jj = np.nonzero(ended)
                dur = t - start[ri, ii, jj]
                dv = det[ri, ii, jj] - start[ri, ii, jj]
                keep = dur >= cfg.min_encounter
                if keep.any():
                    ri, dv = ri[keep], dv[keep]
                    enc_cnt += np.bincount(ri, minlength=nr)
                    missed = np.isnan(dv)
                    if missed.any():
                        miss_cnt += np.bincount(ri[missed], minlength=nr)
                    found = ~missed
                    if found.any():
                        det_cnt += np.bincount(ri[found], minlength=nr)
                        det_sum += np.bincount(ri[found], weights=dv[found], minlength=nr)
                        _group_append(ri[found], dv[found], delay_buckets)

            # onset of a new encounter
            onset = crit & ~active
            if onset.any():
                start[onset] = t
                det[onset] = np.nan
            active = crit.copy()

            # detection: the receiver declares the pair critical from its estimate
            need = active & np.isnan(det)
            if need.any():
                ri, ii, jj = np.nonzero(need)
                tc_e, dc_e = pairwise_geometry(pos[ri, ii], vel[ri, ii],
                                               p_hat_new[ri, ii, jj], v_rx[ri, ii, jj])
                seen = (age_c[ri, ii, jj] <= cfg.T_timeout) & (tc_e >= 0.0) & \
                       (tc_e <= cfg.t_crit) & (dc_e <= cfg.d_crit)
                if seen.any():
                    det[ri[seen], ii[seen], jj[seen]] = t

        # ------------------------------------------------------------------- metrics
        if k >= k_warm and (k % k_sample == 0):
            # --- critical ordered pairs
            m = crit & has
            if crit.any():
                crit_n += crit.sum(axis=(1, 2))
                stale_sum += (crit & (~has | (age > cfg.stale_age))).sum(axis=(1, 2))
                age_sum += np.where(m, age_c, 0.0).sum(axis=(1, 2))
                age_n += m.sum(axis=(1, 2))
                cpv_sum += crit.sum(axis=(1, 2)) / n
                cpv_n += 1.0
            if m.any():
                ri, ii, jj = np.nonzero(m)
                e = np.sqrt(((p_hat_new[ri, ii, jj] - pos[ri, jj]) ** 2).sum(-1))
                age_v = age_c[ri, ii, jj]
                err_sum += np.bincount(ri, weights=e, minlength=nr)
                err_n += np.bincount(ri, minlength=nr)
                _group_append(ri, e, err_buckets)
                _group_append(ri, age_v, age_buckets)

            # --- all in-range pairs (for the redistribution remark of Sec. V-B)
            ma = near & has
            if ma.any():
                ri, ii, jj = np.nonzero(ma)
                e = np.sqrt(((p_hat_new[ri, ii, jj] - pos[ri, jj]) ** 2).sum(-1))
                all_err_sum += np.bincount(ri, weights=e, minlength=nr)
                all_err_n += np.bincount(ri, minlength=nr)

        if verbose and (k % max(1, n_steps // 10) == 0):
            print(f"    t={t:6.1f}s  ({100.0 * k / n_steps:3.0f}%)", flush=True)

    # ------------------------------------------------------------------- wrap up
    def _p95(buckets):
        out = np.full(nr, np.nan)
        for r, parts in enumerate(buckets):
            if parts:
                out[r] = float(np.percentile(np.concatenate(parts), 95))
        return out

    rate = tx_win / (n * T_win)
    with np.errstate(invalid="ignore", divide="ignore"):
        pdr = np.where(att > 0, suc / np.maximum(att, 1.0), np.nan)
        age_mean = np.where(age_n > 0, age_sum / np.maximum(age_n, 1.0), np.nan)
        err_mean = np.where(err_n > 0, err_sum / np.maximum(err_n, 1.0), np.nan)
        all_err = np.where(all_err_n > 0, all_err_sum / np.maximum(all_err_n, 1.0), np.nan)
        stale = np.where(crit_n > 0, stale_sum / np.maximum(crit_n, 1.0), np.nan)
        delay_mean = np.where(det_cnt > 0, det_sum / np.maximum(det_cnt, 1.0), np.nan)
        miss = np.where(enc_cnt > 0, miss_cnt / np.maximum(enc_cnt, 1.0), np.nan)
        cpv = np.where(cpv_n > 0, cpv_sum / np.maximum(cpv_n, 1.0), np.nan)

    return SimResult(
        scheme=scheme,
        n=n,
        n_runs=nr,
        rate=rate,
        pdr=pdr,
        age_mean=age_mean,
        age_p95=_p95(age_buckets),
        err_mean=err_mean,
        err_p95=_p95(err_buckets),
        stale=stale,
        delay_mean=delay_mean,
        delay_p95=_p95(delay_buckets),
        miss=miss,
        all_err_mean=all_err,
        crit_per_veh=cpv,
    )
