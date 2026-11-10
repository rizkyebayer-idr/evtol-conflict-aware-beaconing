"""Conflict geometry of Sec. II-C: TCPA, DCPA and the conflict-risk metric.

All functions are written with broadcasting in mind: the last axis is the
3-D vector axis, every other axis is an arbitrary batch axis.
"""

from __future__ import annotations

import numpy as np

EPS = 1e-9


def pairwise_geometry(pi, vi, pj, vj):
    """TCPA (3) and DCPA (4).

    Parameters
    ----------
    pi, vi, pj, vj : array_like, shape (..., 3)
        Own state (``i``) and neighbour state (``j``); ``j`` is normally the
        dead-reckoned estimate held by ``i``.

    Returns
    -------
    tcpa : ndarray
        Time to closest point of approach [s].  ``+inf`` if the relative
        velocity vanishes; negative when the pair is already diverging.
    dcpa : ndarray
        Distance at closest point of approach [m].
    """
    pi = np.asarray(pi, dtype=np.float64)
    vi = np.asarray(vi, dtype=np.float64)
    pj = np.asarray(pj, dtype=np.float64)
    vj = np.asarray(vj, dtype=np.float64)

    r = pj - pi                      # relative position  r_ij = p_j - p_i
    v = vj - vi                      # relative velocity  v_ij = v_j - v_i

    vv = np.einsum("...k,...k->...", v, v)
    rv = np.einsum("...k,...k->...", r, v)
    rr = np.einsum("...k,...k->...", r, r)

    moving = vv > 1e-8
    inv_vv = np.where(moving, 1.0 / np.where(moving, vv, 1.0), 0.0)

    tcpa = np.where(moving, -rv * inv_vv, np.inf)
    # DCPA^2 = |r|^2 - (r.v)^2/|v|^2  (clipped at 0 against round-off)
    dcpa = np.sqrt(np.maximum(rr - rv * rv * inv_vv, 0.0))
    return tcpa, dcpa


def conflict_risk(dcpa, tcpa, d0, tau0):
    """Pairwise conflict risk (5)-(7): R_D * R_T, with R_T = 0 for TCPA < 0."""
    rd = np.exp(-np.maximum(dcpa, 0.0) / d0)
    rt = np.where(tcpa >= 0.0, np.exp(-np.maximum(tcpa, 0.0) / tau0), 0.0)
    return rd * rt


def risk_to_interval(risk, T_min, T_max):
    """Risk-to-interval mapping (8)."""
    return T_max - risk * (T_max - T_min)
