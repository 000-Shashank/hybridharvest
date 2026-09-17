"""Abstract base class for all energy sources."""
from __future__ import annotations

from abc import ABC, abstractmethod


class EnergySource(ABC):
    """Base class for all harvesting sources.

    Parameters
    ----------
    name : str
        Human-readable identifier for the source, used as the key in
        per-source power dictionaries produced by the energy manager.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def power(self) -> float:
        """Return instantaneous power in Watts.

        Returns
        -------
        float
            Current electrical power output of the source, in Watts.
        """

    @abstractmethod
    def step(self, dt: float, **kwargs) -> float:
        """Advance internal state by dt seconds and return power in Watts.

        Parameters
        ----------
        dt : float
            Timestep duration in seconds.
        **kwargs
            Source-specific exogenous inputs (for example wind speed,
            flow rate, vibration amplitude).

        Returns
        -------
        float
            Power output in Watts after the state update.
        """
