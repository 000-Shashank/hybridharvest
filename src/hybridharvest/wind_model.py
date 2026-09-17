"""Wind turbine power model."""
from __future__ import annotations

import math

from .base import EnergySource


class WindTurbine(EnergySource):
    """Horizontal-axis wind turbine with Betz-limited power extraction.

    P = 0.5 * rho * A * v^3 * Cp

    Parameters
    ----------
    radius : float, optional
        Rotor radius in metres.
    cp : float, optional
        Power coefficient (Betz limit is 0.593).
    rho : float, optional
        Air density in kg/m^3.
    cut_in : float, optional
        Minimum wind speed in m/s below which no power is produced.
    rated : float, optional
        Maximum wind speed in m/s above which the turbine is shut down.
    """

    def __init__(
        self,
        radius: float = 0.3,
        cp: float = 0.35,
        rho: float = 1.225,
        cut_in: float = 2.0,
        rated: float = 12.0,
    ) -> None:
        super().__init__("wind")
        self.radius = radius
        self.cp = cp
        self.rho = rho
        self.cut_in = cut_in
        self.rated = rated
        self.wind_speed = 0.0

    def power(self) -> float:
        """Return instantaneous aerodynamic power in Watts.

        Returns
        -------
        float
            Power in Watts, or ``0.0`` outside the cut-in/rated window.
        """
        v = self.wind_speed
        if v < self.cut_in or v > self.rated:
            return 0.0
        area = math.pi * self.radius ** 2
        return 0.5 * self.rho * area * v ** 3 * self.cp

    def step(self, dt: float, wind_speed: float | None = None) -> float:
        """Update wind speed and return the resulting power.

        Parameters
        ----------
        dt : float
            Timestep duration in seconds. The wind model is quasi-static, so
            this argument does not affect the returned power.
        wind_speed : float or None, optional
            Wind speed in m/s for this step. When ``None`` the previously
            stored speed is reused.

        Returns
        -------
        float
            Power in Watts.

        Raises
        ------
        ValueError
            If ``wind_speed`` is NaN.
        """
        if wind_speed is not None:
            if math.isnan(wind_speed):
                raise ValueError("wind_speed must not be NaN")
            self.wind_speed = wind_speed
        return self.power()
