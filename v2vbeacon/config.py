"""Simulation parameters (Table I) and guidance settings of the mobility model.

The first block holds the airspace parameters of Table I.  The second block
holds the settings of the guidance law behind Sec. II-A (look-ahead distance,
acceleration and climb-rate limits, rate of target re-draw, turn cooldown);
they are not fixed by Table I and are listed once here so that every experiment
uses the same values.  The remaining blocks are timing, beaconing, channel,
metric and Monte Carlo settings.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Config:
    # ------------------------------------------------------------------ airspace
    sector: float = 2000.0                    # side of the square sector L [m]
    corridors: tuple = (-600.0, 0.0, 600.0)   # corridor centre coordinates [m]
    lane_offset: float = 25.0                 # right-hand lane offset [m]
    alt_min: float = 100.0                    # altitude band [m]
    alt_max: float = 300.0
    v_min: float = 20.0                       # airspeed band [m/s]
    v_max: float = 50.0
    phi_max: float = 25.0                     # maximum bank angle [deg]
    p_turn: float = 0.30                      # P(turn onto crossing corridor)
    g: float = 9.81                           # gravitational acceleration [m/s^2]

    # guidance law / manoeuvre limits (see README, implementation notes)
    a_max: float = 2.0                        # |d|v||/dt [m/s^2]
    a_z_max: float = 1.0                      # |d vz/dt| [m/s^2]
    vz_max: float = 2.5                       # climb-rate limit [m/s]
    lookahead: float = 200.0                 # look-ahead distance of the guidance law [m]
    speed_change_rate: float = 1.0 / 25.0     # Poisson rate of airspeed target changes [1/s]
    alt_change_rate: float = 1.0 / 30.0       # Poisson rate of altitude target changes [1/s]
    turn_cooldown: float = 3.0                # no second turn right after a turn [s]
    respawn_margin: float = 100.0             # leaving margin before replacement [m]

    # -------------------------------------------------------------------- timing
    dt: float = 0.05                          # time step [s]
    duration: float = 300.0                   # total simulated time [s]
    warmup: float = 20.0                      # discarded warm-up [s]

    # ----------------------------------------------------------------- beaconing
    T_min: float = 0.1                        # shortest beacon interval [s]
    T_max: float = 2.0                        # longest beacon interval [s]
    T_timeout: float = 6.0                    # neighbour time-out T_out [s]
    d0: float = 150.0                         # distance scale D0 [m]
    tau0: float = 15.0                        # time scale T0 [s]

    # ------------------------------------------------------------------- channel
    R_comm: float = 1000.0                    # communication range Rc [m]
    packet_bytes: int = 200                   # beacon size S [byte]
    bit_rate: float = 1.0e6                   # data rate C [bit/s]
    p_residual: float = 0.01                  # residual loss probability p0

    # ------------------------------------------------------------ metric thresholds
    d_crit: float = 100.0                     # critical encounter: DCPA <= 100 m
    t_crit: float = 15.0                      # critical encounter: TCPA <= 15 s
    stale_age: float = 1.0                    # "stale" if age > 1 s
    min_encounter: float = 1.0                # ignore encounters shorter than 1 s

    # ---------------------------------------------------------------- Monte Carlo
    n_runs: int = 50                          # runs per configuration
    seed: int = 2026                          # master seed

    # ------------------------------------------------------------------ derived
    @property
    def airtime(self) -> float:
        """Channel occupation time of one beacon, tau_p = 8 S / C [s]."""
        return 8.0 * self.packet_bytes / self.bit_rate

    @property
    def omega_max(self) -> float:
        """Maximum heading rate g tan(phi_max)/v, evaluated at v = 1 m/s."""
        import math
        return self.g * math.tan(math.radians(self.phi_max))

    def with_(self, **kw) -> "Config":
        """Return a copy with some fields replaced."""
        return replace(self, **kw)


#: Parameter sets of Table III (risk scales D0 / T0).
RISK_SCALES = (
    (100.0, 10.0),
    (150.0, 15.0),
    (200.0, 20.0),
    (300.0, 30.0),
)

#: Traffic densities of the sweep.
N_LIST = (10, 20, 30, 40, 50)
