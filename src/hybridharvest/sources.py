"""Central registry of energy source metadata.

Every part of HybridHarvest that needs to name, label, or colour a source —
the simulation, the CSV writer, the plots, the dashboard and the example
report — reads from :data:`SOURCES`. Adding a new harvester is therefore a
one-line change here plus its model class.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


#: Single source of truth for source metadata, in canonical display order.
SOURCES: Dict[str, Dict[str, str]] = {
    "wind":      {"label": "Wind Turbine",        "icon": "🌬️"},
    "hydro":     {"label": "Hydro Turbine",       "icon": "💧"},
    "vibration": {"label": "Vibration Harvester", "icon": "📳"},
    "piezo":     {"label": "Piezoelectric Array", "icon": "⚡"},
    "solar":     {"label": "Solar PV",            "icon": "☀️"},
}

#: Sources simulated on every run. ``solar`` is opt-in.
CORE_SOURCES: List[str] = ["wind", "hydro", "vibration", "piezo"]

#: The driving input recorded alongside each source's power trace. Keys are the
#: column names used in the per-category CSV exports; values describe the
#: quantity for the documentation.
INPUTS: Dict[str, Dict[str, str]] = {
    "wind":      {"wind_speed_mps": "Wind speed (m/s)"},
    "hydro":     {"flow_Lpm": "Flow rate (L/min)"},
    "vibration": {"freq_Hz": "Vibration frequency (Hz)",
                  "amp_m": "Displacement amplitude (m)"},
    "piezo":     {"vib_power_W": "Driving vibration power (W)"},
    "solar":     {"irradiance_Wm2": "Irradiance (W/m^2)"},
}


@dataclass
class SourceSeries:
    """Time-series and summary statistics for one energy source.

    Attributes
    ----------
    id : str
        Registry key, e.g. ``"wind"`` or ``"hydro"``.
    label : str
        Human-readable display name, e.g. ``"Wind Turbine"``.
    icon : str
        Emoji used in the dashboard and example report.
    unit : str, optional
        Unit of the recorded values. Defaults to ``"W"``.
    power : list of float
        Instantaneous power samples, one per simulation step.
    """

    id: str
    label: str
    icon: str
    unit: str = "W"
    power: List[float] = field(default_factory=list)

    def total_energy_wh(self, dt: float) -> float:
        """Return the energy harvested over the whole run.

        Parameters
        ----------
        dt : float
            Timestep duration in seconds.

        Returns
        -------
        float
            Energy in watt-hours.
        """
        return sum(self.power) * dt / 3600.0

    def peak_power(self) -> float:
        """Return the maximum recorded power in Watts."""
        return max(self.power) if self.power else 0.0

    def mean_power(self) -> float:
        """Return the arithmetic mean power in Watts."""
        return sum(self.power) / len(self.power) if self.power else 0.0

    def share_pct(self, total_wh: float, dt: float = 1.0) -> float:
        """Return this source's percentage of the aggregate energy.

        Parameters
        ----------
        total_wh : float
            Aggregate energy of *all* sources, in watt-hours, computed over
            the same window and timestep as this series.
        dt : float, optional
            Timestep duration in seconds. Must match the ``dt`` used for
            ``total_wh``. Defaults to 1.0.

        Returns
        -------
        float
            Contribution as a percentage in ``[0, 100]``.
        """
        if total_wh <= 0:
            return 0.0
        return 100.0 * self.total_energy_wh(dt) / total_wh


def make_series(source_id: str) -> SourceSeries:
    """Build an empty :class:`SourceSeries` from the registry.

    Parameters
    ----------
    source_id : str
        Key into :data:`SOURCES`.

    Returns
    -------
    SourceSeries
        A series with ``power`` still empty.
    """
    meta = SOURCES[source_id]
    return SourceSeries(id=source_id, label=meta["label"], icon=meta["icon"])