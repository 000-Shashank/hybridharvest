"""End-to-end simulation loop."""
from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from typing import Dict, List

from .wind_model import WindTurbine
from .water_model import WaterTurbine
from .vibration_model import VibrationHarvester
from .piezo_model import PiezoArray
from .solar_model import SolarPanel
from .energy_manager import EnergyManager
from .storage_model import Supercapacitor
from .load_model import IoTLoad
from .sources import CORE_SOURCES, INPUTS, SourceSeries, SOURCES, make_series


@dataclass
class SimulationResult:
    """Container for a full simulation run.

    Each harvester gets its own :class:`~hybridharvest.sources.SourceSeries`,
    so per-source statistics and contribution shares are available without
    re-deriving them from the aggregate trace.

    Attributes
    ----------
    time : list of float
        Timestamps in seconds.
    sources : dict of str to SourceSeries
        One series per simulated source, keyed by source id.
    inputs : dict of str to dict of str to list of float
        The driving variable recorded for each source at every step, e.g.
        ``inputs["wind"]["wind_speed_mps"]``. Used by the per-category CSV
        export so each file carries its own physical context.
    total_power : list of float
        Aggregate harvested power *after* conversion losses, in Watts.
    storage_voltage : list of float
        Supercapacitor terminal voltage in Volts.
    soc : list of float
        State of charge in ``[0, 1]``.
    load_power : list of float
        Instantaneous load demand in Watts.
    """

    time: List[float] = field(default_factory=list)
    sources: Dict[str, SourceSeries] = field(default_factory=dict)
    inputs: Dict[str, Dict[str, List[float]]] = field(default_factory=dict)
    total_power: List[float] = field(default_factory=list)
    storage_voltage: List[float] = field(default_factory=list)
    soc: List[float] = field(default_factory=list)
    load_power: List[float] = field(default_factory=list)

    def source_inputs(self, source_id: str) -> Dict[str, List[float]]:
        """Return the recorded driving variables for ``source_id``.

        Parameters
        ----------
        source_id : str
            Registry key, e.g. ``"wind"``.

        Returns
        -------
        dict of str to list of float
            Input name to samples, or an empty dict when unknown.
        """
        return self.inputs.get(source_id, {})

    # -- backwards-compatible accessors ------------------------------------
    def _power(self, source_id: str) -> List[float]:
        """Return the raw power list for ``source_id``, or an empty list."""
        series = self.sources.get(source_id)
        return series.power if series is not None else []

    @property
    def wind_power(self) -> List[float]:
        """Wind turbine power samples in Watts."""
        return self._power("wind")

    @property
    def hydro_power(self) -> List[float]:
        """Hydro turbine power samples in Watts."""
        return self._power("hydro")

    @property
    def water_power(self) -> List[float]:
        """Deprecated alias for :attr:`hydro_power`."""
        return self._power("hydro")

    @property
    def vibration_power(self) -> List[float]:
        """Vibration harvester power samples in Watts."""
        return self._power("vibration")

    @property
    def piezo_power(self) -> List[float]:
        """Piezoelectric array power samples in Watts."""
        return self._power("piezo")

    @property
    def solar_power(self) -> List[float]:
        """Solar PV power samples in Watts (empty when solar is disabled)."""
        return self._power("solar")

    # -- aggregate helpers --------------------------------------------------
    def source_energy_wh(self, dt: float) -> float:
        """Total *pre-conversion* energy summed over all sources.

        Parameters
        ----------
        dt : float
            Timestep duration in seconds.

        Returns
        -------
        float
            Energy in watt-hours. This is the correct denominator for
            per-source contribution shares, because
            :attr:`total_power` also includes the converter efficiency.
        """
        return sum(s.total_energy_wh(dt) for s in self.sources.values())

    def total_energy_wh(self, dt: float) -> float:
        """Total harvested energy after conversion losses.

        Parameters
        ----------
        dt : float
            Timestep duration in seconds.

        Returns
        -------
        float
            Energy in watt-hours.
        """
        return sum(self.total_power) * dt / 3600.0


def run_simulation(
    duration_hours: float = 24.0,
    dt: float = 1.0,
    seed: int = 42,
    enable_solar: bool = False,
    piezo_config: str = "parallel",
    piezo_elements: int = 4,
    capacitance: float = 10.0,
    v_max: float = 5.5,
) -> SimulationResult:
    """Run the hybrid harvester simulation.

    Parameters
    ----------
    duration_hours : float, optional
        Simulated time span in hours. Defaults to 24.0.
    dt : float, optional
        Timestep in seconds. Defaults to 1.0.
    seed : int, optional
        Seed for the weather/vibration generator. Defaults to 42.
    enable_solar : bool, optional
        Include the optional solar PV source. Defaults to False.
    piezo_config : {"single", "series", "parallel"}, optional
        Piezoelectric array wiring. Defaults to ``"parallel"``.
    piezo_elements : int, optional
        Number of piezo elements in the array. Defaults to 4.
    capacitance : float, optional
        Supercapacitor capacitance in Farads. Defaults to 10.0.
    v_max : float, optional
        Supercapacitor maximum voltage in Volts. Defaults to 5.5.

    Returns
    -------
    SimulationResult
        The recorded time series for every source and aggregate.
    """
    rng = random.Random(seed)

    wind = WindTurbine()
    hydro = WaterTurbine()
    vib = VibrationHarvester()
    piezo = PiezoArray(config=piezo_config, n_elements=piezo_elements)
    # Spec defaults: a 0.1 m^2 panel at 18% efficiency. Mean output is about
    # 4.5 W across a diurnal cycle, which is proportionate to the 0.6 m
    # diameter wind turbine modelled above.
    solar = SolarPanel() if enable_solar else None

    source_ids = list(CORE_SOURCES)
    if enable_solar:
        source_ids.append("solar")
    sources: Dict[str, SourceSeries] = {sid: make_series(sid) for sid in source_ids}
    inputs: Dict[str, Dict[str, List[float]]] = {
        sid: {name: [] for name in INPUTS[sid]} for sid in source_ids
    }

    manager_sources = [wind, hydro, vib, piezo]
    if solar is not None:
        manager_sources.append(solar)

    manager = EnergyManager(sources=manager_sources)
    storage = Supercapacitor(capacitance=capacitance, v_max=v_max)
    load = IoTLoad()

    result = SimulationResult(sources=sources, inputs=inputs)
    t = 0.0
    total_seconds = duration_hours * 3600.0

    while t < total_seconds:
        # Draw the driving variables first, in a fixed order, so that a given
        # seed reproduces earlier runs exactly.
        wind_speed = rng.uniform(0, 8)
        flow = rng.uniform(0, 3)
        freq = rng.uniform(20, 80)
        # Amplitude is a *displacement in metres*. A 10 g cantilever moves in
        # micrometres to millimetres, so sample 10-100 um. Power scales with
        # A^2, so a 0.1-1.0 m range would produce megawatts.
        amp = rng.uniform(1e-5, 1e-4)

        wind_p = wind.step(dt, wind_speed=wind_speed)
        hydro_p = hydro.step(dt, flow=flow)
        vib_p = vib.step(dt, freq=freq, amp=amp)
        piezo_p = piezo.step(dt, vib_power=vib_p)

        sources["wind"].power.append(wind_p)
        sources["hydro"].power.append(hydro_p)
        sources["vibration"].power.append(vib_p)
        sources["piezo"].power.append(piezo_p)

        inputs["wind"]["wind_speed_mps"].append(wind_speed)
        inputs["hydro"]["flow_Lpm"].append(flow)
        inputs["vibration"]["freq_Hz"].append(freq)
        inputs["vibration"]["amp_m"].append(amp)
        inputs["piezo"]["vib_power_W"].append(vib_p)

        if solar is not None:
            # Simple diurnal model: irradiance peaks at local noon.
            hour_of_day = (t / 3600.0) % 24.0
            irradiance = max(0.0, 1000.0 * (1.0 - abs(hour_of_day - 12.0) / 6.0))
            sources["solar"].power.append(solar.step(dt, irradiance=irradiance))
            inputs["solar"]["irradiance_Wm2"].append(irradiance)

        total = manager.total_power()
        load_p = load.step(dt, t)
        net = total - load_p

        if net > 0:
            storage.charge(net, dt)
        else:
            storage.discharge(-net, dt)

        result.time.append(t)
        result.total_power.append(total)
        result.storage_voltage.append(storage.voltage)
        result.soc.append(storage.soc())
        result.load_power.append(load_p)

        t += dt

    return result


def save_csv(result: SimulationResult, path: str) -> None:
    """Write results to CSV with one column per source.

    The header carries a ``<source>_W`` column for every simulated source,
    followed by the aggregate columns. Only sources that were actually
    simulated appear, so the file is self-describing.

    Parameters
    ----------
    result : SimulationResult
        The simulation output.
    path : str
        Destination CSV path. Parent directories must already exist.
    """
    source_ids = [sid for sid in SOURCES if sid in result.sources]

    header: List[str] = ["time_s"]
    columns: List[List[float]] = [result.time]
    for sid in source_ids:
        header.append(f"{sid}_W")
        columns.append(result.sources[sid].power)

    header.extend(["total_W", "storage_V", "soc", "load_W"])
    columns.extend([
        result.total_power,
        result.storage_voltage,
        result.soc,
        result.load_power,
    ])

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in zip(*columns):
            writer.writerow(row)