#!/usr/bin/env python3
"""Export per-category analyzed data to ``data/processed/<source>/``.

For each source this writes two files:

    example_<source>_24h.csv   time_s + the source's driving inputs
                               + power_W + energy_Wh_cumulative
    stats_<source>.json        summary statistics, including its share of
                               the total harvest

plus a system-wide ``summary.json``. The run uses seed 42, so the committed
data is fully reproducible.

Run with::

    python scripts/export_categorized_data.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hybridharvest import __version__  # noqa: E402
from hybridharvest.simulation import run_simulation  # noqa: E402
from hybridharvest.sources import INPUTS, SOURCES  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data", "processed")

HOURS = 24.0
DT = 1.0
SEED = 42

#: Keep only every Nth sample in the committed CSVs. At full resolution the
#: five files total ~13 MB, which is a lot of repository for data that
#: regenerates in seconds. The cumulative-energy column is computed at full
#: resolution and then sampled, so its values stay exact.
CSV_STRIDE = 60

#: Wind speeds at or above this count as operating hours.
CUT_IN_MPS = 2.0

#: Format for every numeric CSV cell. ``%g`` rather than ``%f`` because the
#: vibration amplitude is ~1e-5 m: a fixed-point format would round it to two
#: significant digits, and power scales with amplitude squared, so a reader
#: recomputing from the file would get a badly wrong answer.
CELL_FMT = "{:.10g}"


def _source_extras(sid: str, result, dt: float) -> dict:
    """Return the source-specific statistics for ``sid``."""
    inputs = result.source_inputs(sid)
    series = result.sources[sid]

    if sid == "wind":
        speeds = inputs["wind_speed_mps"]
        return {
            "cut_in_hours": round(
                sum(1 for v in speeds if v >= CUT_IN_MPS) * dt / 3600.0, 4
            ),
        }
    if sid == "hydro":
        flows = inputs["flow_Lpm"]
        return {"mean_flow_Lpm": round(sum(flows) / len(flows), 6) if flows else 0.0}
    if sid == "vibration":
        freqs = inputs["freq_Hz"]
        amps = inputs["amp_m"]
        return {
            "mean_freq_Hz": round(sum(freqs) / len(freqs), 6) if freqs else 0.0,
            "mean_amp_um": round(1e6 * sum(amps) / len(amps), 4) if amps else 0.0,
        }
    if sid == "piezo":
        vib_wh = result.sources["vibration"].total_energy_wh(dt)
        elec_wh = series.total_energy_wh(dt)
        if vib_wh > 0:
            # Electrical energy out per vibration energy in, per element
            n_elements = getattr(result.sources["piezo"], "n_elements", 4)  # fallback
            eff = elec_wh / (vib_wh * n_elements)
        else:
            eff = 0.0
        return {
            "efficiency": round(eff, 6),
        }
    if sid == "solar":
        irradiance = inputs["irradiance_Wm2"]
        return {
            "daily_yield_Wh": round(series.total_energy_wh(dt), 6),
            "peak_irradiance_Wm2": round(max(irradiance), 4) if irradiance else 0.0,
        }
    return {}


def export_source(result, sid: str, dt: float, stride: int) -> dict:
    """Write the CSV and stats JSON for one source.

    Parameters
    ----------
    result : SimulationResult
        A completed run.
    sid : str
        Registry key, e.g. ``"wind"``.
    dt : float
        Timestep in seconds.
    stride : int
        Sampling interval for the CSV, in steps.

    Returns
    -------
    dict
        The statistics written to ``stats_<sid>.json``.
    """
    meta = SOURCES[sid]
    series = result.sources[sid]
    folder = os.path.join(DATA, sid)
    os.makedirs(folder, exist_ok=True)

    # Cumulative energy at full resolution, then sampled.
    cumulative = []
    running = 0.0
    for power in series.power:
        running += power * dt / 3600.0
        cumulative.append(running)

    input_names = list(INPUTS[sid])
    csv_name = f"example_{sid}_24h.csv"
    csv_path = os.path.join(folder, csv_name)

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        handle.write(
            "time_s," + ",".join(input_names) + ",power_W,energy_Wh_cumulative\n"
        )
        for i in range(0, len(result.time), stride):
            cells = [f"{result.time[i]:.1f}"]
            cells += [f"{result.inputs[sid][n][i]:.10g}" for n in input_names]
            cells.append(f"{series.power[i]:.10g}")
            cells.append(f"{cumulative[i]:.10g}")
            handle.write(",".join(cells) + "\n")

    # -- statistics --------------------------------------------------------
    source_wh = result.source_energy_wh(dt)
    samples = len(series.power)
    powers = series.power
    operating = sum(1 for p in powers if p > 0.0)
    duration_h = samples * dt / 3600.0
    peak = series.peak_power()

    stats = {
        "source": sid,
        "label": meta["label"],
        "icon": meta["icon"],
        "duration_hours": round(duration_h, 6),
        "samples": samples,
        "dt_s": dt,
        "seed": SEED,
        "csv_file": csv_name,
        "csv_stride": stride,
        "peak_power_W": round(peak, 6),
        "mean_power_W": round(series.mean_power(), 6),
        "min_power_W": round(min(powers), 6) if powers else 0.0,
        "std_power_W": round(statistics.pstdev(powers), 6) if powers else 0.0,
        "total_energy_Wh": round(series.total_energy_wh(dt), 6),
        "share_pct": round(series.share_pct(source_wh, dt), 4),
        "operating_hours": round(operating * dt / 3600.0, 4),
        "downtime_hours": round((samples - operating) * dt / 3600.0, 4),
        "capacity_factor": round(series.mean_power() / peak, 6) if peak > 0 else 0.0,
        "inputs": INPUTS[sid],
    }
    stats.update(_source_extras(sid, result, dt))

    json_path = os.path.join(folder, f"stats_{sid}.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
        handle.write("\n")

    return stats


def main() -> int:
    os.makedirs(DATA, exist_ok=True)

    result = run_simulation(
        duration_hours=HOURS, dt=DT, seed=SEED, enable_solar=True
    )

    stats_by_source = {}
    for sid in result.sources:
        stats = export_source(result, sid, DT, CSV_STRIDE)
        stats_by_source[sid] = stats
        print(
            f"[ok] {sid:<10} {stats['total_energy_Wh']:>10.4f} Wh "
            f"({stats['share_pct']:>6.2f}%)  "
            f"data/processed/{sid}/example_{sid}_24h.csv"
        )

    source_wh = result.source_energy_wh(DT)
    total_wh = result.total_energy_wh(DT)
    load_wh = sum(result.load_power) * DT / 3600.0

    summary = {
        "generated_by": "scripts/export_categorized_data.py",
        "hybridharvest_version": __version__,
        "duration_hours": HOURS,
        "dt_s": DT,
        "seed": SEED,
        "csv_stride": CSV_STRIDE,
        "sources_simulated": list(result.sources),
        "total_energy_Wh_preconversion": round(source_wh, 6),
        "total_energy_Wh_after_conversion": round(total_wh, 6),
        "load_energy_Wh": round(load_wh, 6),
        "peak_total_power_W": round(max(result.total_power), 6),
        "mean_total_power_W": round(
            sum(result.total_power) / len(result.total_power), 6
        ),
        "conversion_efficiency": 0.85,
        "sources": {
            sid: {
                "label": stats_by_source[sid]["label"],
                "icon": stats_by_source[sid]["icon"],
                "energy_Wh": stats_by_source[sid]["total_energy_Wh"],
                "share_pct": stats_by_source[sid]["share_pct"],
                "peak_power_W": stats_by_source[sid]["peak_power_W"],
                "csv": f"data/processed/{sid}/example_{sid}_24h.csv",
                "stats": f"data/processed/{sid}/stats_{sid}.json",
            }
            for sid in result.sources
        },
    }

    summary_path = os.path.join(DATA, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")

    print()
    print(f"[ok] sources sum to      {source_wh:>10.4f} Wh (pre-conversion)")
    print(f"[ok] after conversion    {total_wh:>10.4f} Wh")
    print(f"[ok] summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())