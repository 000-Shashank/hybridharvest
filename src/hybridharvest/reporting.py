"""Plotting utilities."""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .simulation import SimulationResult
from .sources import SOURCES


def _ensure(path: str) -> None:
    """Create directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def plot_results(result: SimulationResult, output_dir: str) -> None:
    """Generate and save the aggregate plots for a simulation run.

    Writes ``per_source_power.png``, ``per_source_stacked.png``,
    ``total_power.png``, ``storage_voltage_soc.png`` and
    ``load_vs_harvest.png``.

    Parameters
    ----------
    result : SimulationResult
        The simulation output.
    output_dir : str
        Directory where plots will be saved.
    """
    _ensure(output_dir)
    time = result.time

    # --- Per-source power, one line each ---------------------------------
    plt.figure(figsize=(10, 6))
    for series in result.sources.values():
        if series.power:
            plt.plot(time, series.power, label=series.label, linewidth=1)
    plt.xlabel("time (s)")
    plt.ylabel("power (W)")
    plt.title("Per-source power")
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "per_source_power.png"))
    plt.close()

    # --- Per-source stacked area -----------------------------------------
    plt.figure(figsize=(10, 6))
    labels = [s.label for s in result.sources.values() if s.power]
    arrays = [s.power for s in result.sources.values() if s.power]
    if arrays:
        plt.stackplot(time, *arrays, labels=labels, alpha=0.85)
        plt.legend(loc="upper left")
    plt.xlabel("time (s)")
    plt.ylabel("power (W)")
    plt.title("Per-source power (stacked)")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "per_source_stacked.png"))
    plt.close()

    # --- Total harvested power -------------------------------------------
    plt.figure(figsize=(10, 6))
    plt.plot(time, result.total_power, linewidth=2, color="tab:green")
    plt.xlabel("time (s)")
    plt.ylabel("power (W)")
    plt.title("Total harvested power")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "total_power.png"))
    plt.close()

    # --- Storage voltage and state of charge ------------------------------
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(time, result.storage_voltage, color="tab:blue", linewidth=2)
    ax1.set_xlabel("time (s)")
    ax1.set_ylabel("storage voltage (V)", color="tab:blue")
    ax2 = ax1.twinx()
    ax2.plot(time, result.soc, color="tab:red", linewidth=2)
    ax2.set_ylabel("state of charge", color="tab:red")
    plt.title("Storage voltage and SoC")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "storage_voltage_soc.png"))
    plt.close()

    # --- Load vs harvest --------------------------------------------------
    plt.figure(figsize=(10, 6))
    plt.plot(time, result.total_power, label="harvested",
             linewidth=2, color="tab:green")
    plt.plot(time, result.load_power, label="load",
             linewidth=2, color="tab:orange")
    plt.xlabel("time (s)")
    plt.ylabel("power (W)")
    plt.title("Load vs harvest")
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "load_vs_harvest.png"))
    plt.close()


def plot_source_detail(
    result: SimulationResult, source_id: str, output_dir: str
) -> None:
    """Save a standalone power plot for a single source.

    Writes ``<source_id>_power.png``. Does nothing if that source was not
    part of the run, or recorded no samples.

    Parameters
    ----------
    result : SimulationResult
        The simulation output.
    source_id : str
        Registry key, e.g. ``"wind"``. Must exist in :data:`SOURCES`.
    output_dir : str
        Directory where the plot will be saved.
    """
    series = result.sources.get(source_id)
    if series is None or not series.power:
        return

    _ensure(output_dir)
    plt.figure(figsize=(10, 6))
    plt.plot(result.time, series.power, linewidth=2)
    plt.xlabel("time (s)")
    plt.ylabel(f"power ({series.unit})")
    plt.title(f"{series.label} power output")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{source_id}_power.png"))
    plt.close()


def plot_all_source_details(result: SimulationResult, output_dir: str) -> None:
    """Save one detail plot per simulated source.

    Parameters
    ----------
    result : SimulationResult
        The simulation output.
    output_dir : str
        Directory where the plots will be saved.
    """
    for source_id in SOURCES:
        plot_source_detail(result, source_id, output_dir)