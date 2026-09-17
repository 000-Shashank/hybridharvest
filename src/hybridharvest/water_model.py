"""Water turbine power model."""
from __future__ import annotations
from .base import EnergySource


class WaterTurbine(EnergySource):
    """Micro-hydro turbine.

    P = rho * g * Q * H * eta  (Q in m^3/s)
    """

    def __init__(
        self,
        head: float = 2.0,
        eta: float = 0.6,
        rho: float = 1000.0,
        g: float = 9.81,
    ) -> None:
        super().__init__("water")
        self.head = head
        self.eta = eta
        self.rho = rho
        self.g = g
        self.flow = 0.0  # m^3/s

    def power(self) -> float:
        """Return instantaneous hydraulic power in Watts.

        Returns
        -------
        float
            Power in Watts.
        """
        return self.rho * self.g * self.flow * self.head * self.eta

    def step(self, dt: float, flow: float | None = None) -> float:
        """Advance the flow state and return power.

        Parameters
        ----------
        dt : float
            Timestep duration in seconds. The model is quasi-static.
        flow : float or None, optional
            Volumetric flow rate in litres per minute (L/min). If provided,
            the internal state is updated (converted to m^3/s).

        Returns
        -------
        float
            Power in Watts after the update.
        """
        if flow is not None:
            self.flow = flow / 60000.0  # L/min -> m^3/s
        return self.power()