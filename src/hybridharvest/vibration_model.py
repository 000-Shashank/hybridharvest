"""Vibration energy harvester model (resonant cantilever)."""
from __future__ import annotations
import math
from .base import EnergySource


class VibrationHarvester(EnergySource):
    """Resonant cantilever harvester.

    P = m * zeta_e * A^2 * omega_n^3 / (zeta_m + zeta_e)^2
    """

    def __init__(
        self,
        mass: float = 0.01,
        zeta_m: float = 0.02,
        zeta_e: float = 0.01,
        omega_n: float = 2 * math.pi * 50,
    ) -> None:
        super().__init__("vibration")
        self.mass = mass
        self.zeta_m = zeta_m
        self.zeta_e = zeta_e
        self.omega_n = omega_n
        self.freq = 0.0
        self.amp = 0.0

    def power(self) -> float:
        """Return instantaneous power in Watts.

        Returns
        -------
        float
            Power in Watts, or zero if amplitude is non-positive.
        """
        if self.amp <= 0:
            return 0.0
        denom = (self.zeta_m + self.zeta_e) ** 2
        return (
            self.mass * self.zeta_e * self.amp ** 2 * self.omega_n ** 3 / denom
        )

    def step(
        self, dt: float, freq: float | None = None, amp: float | None = None
    ) -> float:
        """Advance the harvester state and return power.

        Parameters
        ----------
        dt : float
            Timestep duration in seconds. The model is quasi-static.
        freq : float or None, optional
            Vibration frequency in Hz. If provided, updates internal state.
        amp : float or None, optional
            Vibration amplitude in metres. If provided, updates internal state.

        Returns
        -------
        float
            Power in Watts after the update.
        """
        if freq is not None:
            self.freq = freq
        if amp is not None:
            self.amp = amp
        return self.power()