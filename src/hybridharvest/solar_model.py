"""Solar panel model for hybrid energy harvesting."""

from __future__ import annotations
from .base import EnergySource


class SolarPanel(EnergySource):
    """Simple PV panel model.

    P = G * A * eta   (G = irradiance in W/m^2)
    """
    def __init__(self, area: float = 0.1, eta: float = 0.18) -> None:
        super().__init__("solar")
        self.area = area
        self.eta = eta
        self.irradiance = 0.0

    def power(self) -> float:
        return self.irradiance * self.area * self.eta

    def step(self, dt: float, irradiance: float | None = None) -> float:
        if irradiance is not None:
            self.irradiance = max(0.0, irradiance)
        return self.power()