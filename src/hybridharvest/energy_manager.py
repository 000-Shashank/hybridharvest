"""Energy manager combining all sources."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from .base import EnergySource


@dataclass
class EnergyManager:
    """Aggregates source powers with conversion and storage efficiency."""

    sources: List[EnergySource]
    conversion_efficiency: float = 0.85
    storage_efficiency: float = 0.92

    def total_power(self) -> float:
        """Return the aggregate electrical power after conversion losses.

        Returns
        -------
        float
            Sum of all source powers multiplied by the conversion efficiency.
        """
        raw = sum(s.power() for s in self.sources)
        return raw * self.conversion_efficiency

    def net_power(self, load_power: float) -> float:
        """Return power available to (or drawn from) storage.

        Parameters
        ----------
        load_power : float
            Instantaneous load demand in Watts.

        Returns
        -------
        float
            Positive when the harvest exceeds the load.
        """
        return self.total_power() * self.storage_efficiency - load_power

    def step(self, dt: float) -> dict:
        """Advance every source by ``dt`` and return a summary dictionary.

        Parameters
        ----------
        dt : float
            Timestep duration in seconds.

        Returns
        -------
        dict
            ``{"per_source": {name: power}, "total": power}``
        """
        per_source = {s.name: s.step(dt) for s in self.sources}
        return {
            "per_source": per_source,
            "total": sum(per_source.values()) * self.conversion_efficiency,
        }