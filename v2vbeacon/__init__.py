"""Reproducible simulator for

    "Conflict-Risk-Aware Adaptive V2V Beaconing for eVTOL Air Taxis in
     Urban Air Corridors"

The package is a pure NumPy implementation of the system model of Section II,
the beaconing rule of Section III and the metrics of Section IV.  Every Monte
Carlo run of one configuration is vectorised (the leading axis of every state
array is the Monte Carlo run index).

Public API
----------
Config          all simulation parameters (Table I)
Mobility        corridor mobility of the eVTOL air taxis (Sec. II-A)
simulate()      one Monte Carlo configuration for one beaconing scheme
sweep           helpers that run/caches the full N-sweep used by Figs. 3-4
"""

from .config import Config
from .mobility import Mobility
from .engine import simulate, SimResult, pairwise_geometry

__all__ = ["Config", "Mobility", "simulate", "SimResult", "pairwise_geometry"]
