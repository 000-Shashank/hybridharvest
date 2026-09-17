# Data Directory

Two tiers, matching how the data is actually produced and used.

## `raw/`

Original, unprocessed captures — meter logs, field recordings, vendor exports.
**Not committed.** Only the `.gitkeep` placeholders are tracked, one per
category:

```
data/raw/
├── wind/.gitkeep
├── hydro/.gitkeep
├── vibration/.gitkeep
├── piezo/.gitkeep
└── solar/.gitkeep
```

## `processed/`

Analyzed, per-category datasets. **Committed**, so a reviewer can click through
them on GitHub without running anything.

Each category folder holds one CSV (the time series) and one JSON (its summary
statistics):

```
data/processed/
├── summary.json                    system-wide totals and shares
├── wind/
│   ├── example_wind_24h.csv
│   └── stats_wind.json
├── hydro/
│   ├── example_hydro_24h.csv
│   └── stats_hydro.json
├── vibration/
│   ├── example_vibration_24h.csv
│   └── stats_vibration.json
├── piezo/
│   ├── example_piezo_24h.csv
│   └── stats_piezo.json
└── solar/
    ├── example_solar_24h.csv
    └── stats_solar.json
```

Regenerate everything with:

```bash
python scripts/export_categorized_data.py
```

The export runs `run_simulation(duration_hours=24, dt=1.0, seed=42)`, so the
committed data is fully reproducible.

## CSV schema

Every category CSV shares three columns and adds its own physical context:

| Column | Meaning |
|---|---|
| `time_s` | Simulation time in seconds |
| `power_W` | Instantaneous power for this source, in Watts |
| `energy_Wh_cumulative` | Energy accumulated since `t=0`, in Wh |

Source-specific columns sit between them:

| Category | Extra columns |
|---|---|
| 🌬️ Wind | `wind_speed_mps` |
| 💧 Hydro | `flow_Lpm` |
| 📳 Vibration | `freq_Hz`, `amp_m` |
| ⚡ Piezo | `vib_power_W` |
| ☀️ Solar | `irradiance_Wm2` |

Example — `wind/example_wind_24h.csv`:

```csv
time_s,wind_speed_mps,power_W,energy_Wh_cumulative
0.0,5.115414388,8.113513843,0.002253753845
60.0,3.353799323,2.28653439,0.1364758179
```

> **Resolution.** The files are sampled every 60th step, so `time_s` advances in
> 60 s increments. The full 1-second run is 86,400 rows per source; committing
> that would add ~13 MB to the repository for data that regenerates in seconds.
> The cumulative-energy column is computed at full resolution and then sampled,
> so its values are exact.

## JSON schema

`stats_<source>.json` carries a common block plus source-specific extras:

```json
{
  "source": "wind",
  "label": "Wind Turbine",
  "icon": "🌬️",
  "duration_hours": 24.0,
  "samples": 86400,
  "dt_s": 1.0,
  "seed": 42,
  "csv_file": "example_wind_24h.csv",
  "csv_stride": 60,

  "peak_power_W": 31.033708,
  "mean_power_W": 7.727378,
  "min_power_W": 0.0,
  "std_power_W": 8.820052,
  "total_energy_Wh": 185.45708,
  "share_pct": 61.5235,
  "operating_hours": 18.01,
  "downtime_hours": 5.99,
  "capacity_factor": 0.249
}
```

`share_pct` is relative to the sum of all sources' energies, so the shares across
the five files add to 100 %. `capacity_factor` is mean power divided by peak
power. `operating_hours` counts steps where power was above zero.

Source-specific extras:

| Category | Extra fields |
|---|---|
| 🌬️ Wind | `cut_in_hours` — hours at or above the 2 m/s cut-in |
| 💧 Hydro | `mean_flow_Lpm` |
| 📳 Vibration | `mean_freq_Hz`, `mean_amp_um` |
| ⚡ Piezo | `efficiency` — piezo electrical energy ÷ (driving vibration energy × element count) |
| ☀️ Solar | `daily_yield_Wh`, `peak_irradiance_Wm2` |

## Uploading your own data

The Streamlit dashboard has an **📤 Upload Data** tab. Pick a category, drop in
a CSV, and it will validate the schema, plot the series, and compute the same
statistics.

Minimum required columns:

- `time_s` — numeric
- `power_W` — numeric

Everything else is preserved and shown. A plain two-column file
(`time_s,power_W`) works fine. The tab also accepts the main
`output/csv/simulation.csv` shape by reading the matching `<category>_W` column,
so you can upload a whole-system run and view one category from it.
