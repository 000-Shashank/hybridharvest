"""Piezoelectric array model."""
from __future__ import annotations
from .base import EnergySource


class PiezoArray(EnergySource):
    """Piezo array converting vibration power to electrical power.

    Configurations:
      - single:   eta = 0.35
      - series:   eta = 0.45, higher voltage
      - parallel: eta = 0.50, higher current
    """

    _ETA = {"single": 0.35, "series": 0.45, "parallel": 0.50}

    def __init__(self, config: str = "single", n_elements: int = 1) -> None:
        super().__init__("piezo")
        if config not in self._ETA:
            raise ValueError(f"Unknown config: {config}")
        self.config = config
        self.n_elements = n_elements
        self.vib_power = 0.0

    def power(self) -> float:
        """Return electrical power output in Watts.

        Returns
        -------
        float
            Vibration power scaled by the configuration efficiency and the
            number of elements.
        """
        eta = self._ETA[self.config]
        return self.vib_power * eta * self.n_elements

    def step(self, dt: float, vib_power: float | None = None) -> float:
        """Update the input vibration power and return electrical power.

        Parameters
        ----------
        dt : float
            Timestep duration in seconds. The model is quasi-static.
        vib_power : float or None, optional
            Mechanical vibration power in Watts supplied to the array.

        Returns
        -------
        float
            Electrical power in Watts after the update.
        """
        if vib_power is not None:
            self.vib_power = vib_power
        return self.power()