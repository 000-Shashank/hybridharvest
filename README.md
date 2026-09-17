# HybridHarvest

**Modular simulation, control and validation framework for hybrid renewable
energy harvesting.**

HybridHarvest models several harvesters feeding a single energy manager, which
charges a supercapacitor that powers a duty-cycled IoT load. Every source is
tracked, plotted and exported as **its own category**, so you can see where the
energy actually comes from — the same way a real SCADA dashboard separates wind,
hydro and solar strings.

- Version: 0.1.0 · Python 3.11+ · MIT
- Full ASCII documentation: [`README.txt`](README.txt)
- Pre-generated 24 h run: [`examples/example_report.md`](examples/example_report.md)

---

## Per-Source Reporting

Each source is a first-class category: its own metric tile, its own expandable
chart, its own CSV column.

| Icon | Source | Physical model | Governing relation |
|---|---|---|---|
| 🌬️ | Wind Turbine | Horizontal-axis turbine, Betz-limited | `P = 0.5 · ρ · A · v³ · Cp` |
| 💧 | Hydro Turbine | Micro-hydro turbine | `P = ρ · g · Q · H · η` |
| 📳 | Vibration Harvester | Resonant cantilever | `P = m · ζe · A² · ωn³ / (ζm + ζe)²` |
| ⚡ | Piezoelectric Array | Array, single / series / parallel | `P = P_vib · η_config · n_elements` |
| ☀️ | Solar PV *(optional)* | Photovoltaic panel | `P = G · A · η` |

`hydro` replaced the old display name `water`; the internal class is still
`WaterTurbine`, so nothing downstream breaks.

The registry in [`src/hybridharvest/sources.py`](src/hybridharvest/sources.py) is
the single source of truth — the dashboard, the CSV writer, the plots and the
example report all read from it. **Adding a new source is one dict entry plus its
model class.**

### Example output

From a 24-hour run with solar enabled, seed 42:

| Source | Peak (W) | Mean (W) | Energy (Wh) | Share (%) |
|---|---|---|---|---|
| 🌬️ Wind Turbine | 31.0337 | 7.7274 | 185.4571 | 61.52 |
| 💧 Hydro Turbine | 0.5886 | 0.2943 | 7.0642 | 2.34 |
| 📳 Vibration Harvester | 0.0345 | 0.0128 | 0.3066 | 0.10 |
| ⚡ Piezoelectric Array | 0.0689 | 0.0255 | 0.6131 | 0.20 |
| ☀️ Solar PV | 18.0000 | 4.5000 | 108.0000 | 35.83 |
| **Total** | — | — | **301.4410** | **100.00** |

Shares are relative to the sum of all sources, so they add to 100 %. The
*harvested* total is lower than that sum because it is measured after the 0.85
converter efficiency — the gap **is** the conversion loss.

### Categorized CSV

`save_csv` writes one column per source, ready for Excel, pandas or MATLAB:

```csv
time_s,wind_W,hydro_W,vibration_W,piezo_W,solar_W,total_W,storage_V,soc,load_W
0.0,8.1135,0.0147,0.0031,0.0062,0.0,6.9170,1.1277,0.0420,0.005
60.0,2.2865,0.3435,0.0305,0.0610,0.0,2.3134,5.5000,1.0000,0.005
...
```

Only sources that were actually simulated appear, so the file is
self-describing. A 24 h run at 1-minute resolution (1,440 rows, 200 KB) is
checked in at
[`examples/data/example_simulation.csv`](examples/data/example_simulation.csv);
regenerate the full 1-second version with `scripts/generate_example_report.py`.

---

## Quickstart

```bash
git clone https://github.com/000-Shashank/hybridharvest.git
cd hybridharvest
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ui]"

# Run a 24 h simulation with all five sources
python scripts/run_simulation.py --hours 24 --solar --out output/

# Regenerate the checked-in example run and report
python scripts/generate_example_report.py

# Test suite
pytest -q

# Dashboard
streamlit run app/dashboard.py     # http://localhost:8501
```

## Dashboard

Four tabs:

| Tab | Contents |
|---|---|
| 📊 Simulation | Per-source metric tiles with share %, system totals, one expandable chart per source, stacked aggregate area, load vs harvest, storage voltage + SoC, CSV download |
| 📤 Upload Data | Load the per-category CSVs from `data/processed/` (or your own) to inspect a run without simulating — each file is validated, then summarised with the same tiles and charts |
| 📖 Help & Usage | Quick start, parameter reference, the four physics models, how to read each chart, tips, troubleshooting, glossary |
| ℹ️ About | Architecture table, reproduction commands, how to add a source |

Sidebar controls: duration, timestep, seed, piezo configuration and element
count, optional solar PV, storage capacitance, output directory, and a **Use
example data** toggle that renders the checked-in 24 h run without simulating, and an **Also write PNG plots** toggle (off by default; the dashboard draws with Plotly, so the matplotlib files are only worth generating if you want them on disk).

## Deployment

The Streamlit dashboard is deployed to Streamlit Community Cloud.

### Streamlit Community Cloud

1. Push the project to a public GitHub repository.
2. Go to https://share.streamlit.io
3. Click "New app".
4. Select your repo, branch, and main file path: `app/dashboard.py`
5. Click "Deploy".

Notes:
   - Public apps are free.
   - Apps sleep after 7 days of no traffic.
   - First access after sleep triggers a 30-60 second cold start.
   - The AI layer is disabled by default (mock mode), so no API keys are required.

## Command line

```
python scripts/run_simulation.py [OPTIONS]

  --hours FLOAT          Simulation duration in hours   (default: 24.0)
  --dt FLOAT             Timestep in seconds            (default: 1.0)
  --seed INT             Random seed                    (default: 42)
  --out PATH             Output directory               (default: output)
  --solar                Include the optional solar PV source
  --piezo-config {single,series,parallel}
  --piezo-elements INT   Number of piezo elements       (default: 4)
  --ai                   Enable AI summarization (requires API key)
```

Prints a per-source contribution table plus the post-conversion total.

## Project structure

```
hybridharvest/
├── README.md                     This file
├── README.txt                    Full ASCII documentation
├── pyproject.toml                Package metadata + build config
├── requirements.txt              Dependencies (Streamlit Cloud reads this)
├── .streamlit/config.toml        Streamlit theme + server settings
├── src/hybridharvest/
│   ├── base.py                   EnergySource abstract class
│   ├── sources.py                SOURCES registry + SourceSeries statistics
│   ├── wind_model.py             WindTurbine
│   ├── water_model.py            WaterTurbine  (displayed as "Hydro")
│   ├── vibration_model.py        VibrationHarvester
│   ├── piezo_model.py            PiezoArray
│   ├── solar_model.py            SolarPanel (optional)
│   ├── energy_manager.py         EnergyManager
│   ├── storage_model.py          Supercapacitor
│   ├── load_model.py             IoTLoad
│   ├── simulation.py             run_simulation, SimulationResult, save_csv
│   └── reporting.py              Aggregate + per-source figures
├── tests/                        pytest suite
├── scripts/
│   ├── run_simulation.py
│   └── generate_example_report.py
├── app/dashboard.py              Streamlit dashboard
└── examples/
    ├── example_report.md         Generated 24 h report
    ├── data/                     example_simulation.csv
    └── plots/                    One PNG per source + aggregates
```

## Design notes

**Per-source `SourceSeries`.** Each harvester owns a series object carrying its
power trace plus `peak_power()`, `mean_power()`, `total_energy_wh(dt)` and
`share_pct(total_wh, dt)`. No more parallel flat lists.

**Backwards-compatible accessors.** `result.wind_power` and friends still return
the raw lists, so existing code and tests keep working unchanged.

**Two scales worth knowing.** Per-source series are pre-conversion; the reported
total is post-conversion (× 0.85). And the modelled hardware spans a wide
range — the 0.6 m diameter wind turbine peaks near 31 W while the vibration
harvester peaks near 34 mW — so wind dominates the stacked view. The per-source
charts are where the small contributors are readable.

## Testing

```bash
pytest -q
pytest --cov=hybridharvest --cov-report=term
```

The suite covers every physical model, the energy manager, storage clamping, the
load duty cycle, the source registry and statistics, the simulation loop, the
CSV schema, and regression-guards the vibration amplitude scale.

## License

MIT — see [`README.txt`](README.txt) for the full text.
