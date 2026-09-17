"""HybridHarvest Streamlit dashboard.

Interactive front-end for the HybridHarvest simulation framework. Reports every
energy source as its own category — its own metric, its own chart, its own CSV
column — alongside the aggregate system views.

Run with::

    streamlit run app/dashboard.py
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from hybridharvest import __version__  # noqa: E402
from hybridharvest.reporting import plot_all_source_details, plot_results  # noqa: E402
from hybridharvest.simulation import run_simulation, save_csv  # noqa: E402
from hybridharvest.sources import INPUTS, SOURCES, SourceSeries  # noqa: E402

st.set_page_config(
    page_title="HybridHarvest Dashboard",
    page_icon="⚡",
    layout="wide",
)

EXAMPLE_CSV = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "examples", "data",
    "example_simulation.csv",
)

#: Upper bound on the points handed to a single Plotly trace. Drawing 86,400
#: samples takes the browser about a minute and shows no more detail than a
#: couple of thousand do; statistics are unaffected because they are computed
#: from the full-resolution series.
MAX_PLOT_POINTS = 3000


# ---------------------------------------------------------------------------
# Uniform in-memory run representation
# ---------------------------------------------------------------------------
@dataclass
class RunData:
    """A simulation run in a form the UI can render.

    Built either from a :class:`~hybridharvest.simulation.SimulationResult`
    or from a previously exported CSV, so the dashboard behaves identically
    for live runs and for the checked-in example data.
    """

    time: List[float]
    sources: Dict[str, SourceSeries]
    total_power: List[float]
    storage_voltage: List[float]
    soc: List[float]
    load_power: List[float]
    dt: float

    def source_energy_wh(self) -> float:
        """Pre-conversion energy summed over every source."""
        return sum(s.total_energy_wh(self.dt) for s in self.sources.values())

    def total_energy_wh(self) -> float:
        """Post-conversion harvested energy."""
        return sum(self.total_power) * self.dt / 3600.0

    def load_energy_wh(self) -> float:
        """Energy consumed by the load."""
        return sum(self.load_power) * self.dt / 3600.0


def run_from_result(result, dt: float) -> RunData:
    """Adapt a SimulationResult to :class:`RunData`."""
    return RunData(
        time=result.time,
        sources=result.sources,
        total_power=result.total_power,
        storage_voltage=result.storage_voltage,
        soc=result.soc,
        load_power=result.load_power,
        dt=dt,
    )


def run_from_csv(df: pd.DataFrame) -> RunData:
    """Rebuild a :class:`RunData` from an exported CSV.

    The timestep is inferred from the time column rather than taken from the
    sidebar, so a downsampled example file reports its own effective ``dt``
    and its energy totals stay correct.

    Parameters
    ----------
    df : pandas.DataFrame
        Frame with the ``<source>_W`` / ``time_s`` / aggregate columns written
        by :func:`~hybridharvest.simulation.save_csv`.

    Returns
    -------
    RunData
        The reconstructed run.
    """
    times = df["time_s"].tolist()
    dt = (times[1] - times[0]) if len(times) > 1 else 0.0

    sources: Dict[str, SourceSeries] = {}
    for sid, meta in SOURCES.items():
        column = f"{sid}_W"
        if column in df.columns:
            sources[sid] = SourceSeries(
                id=sid,
                label=meta["label"],
                icon=meta["icon"],
                power=df[column].tolist(),
            )
    return RunData(
        time=times,
        sources=sources,
        total_power=df["total_W"].tolist(),
        storage_voltage=df["storage_V"].tolist(),
        soc=df["soc"].tolist(),
        load_power=df["load_W"].tolist(),
        dt=dt,
    )


# ---------------------------------------------------------------------------
# Uploaded per-category data
# ---------------------------------------------------------------------------
@dataclass
class CategoryData:
    """One uploaded per-category dataset.

    Deliberately narrower than :class:`RunData`: an uploaded file describes a
    single harvester, so there is no aggregate, no storage and no load to
    report — only that source's power trace and its driving inputs.

    Attributes
    ----------
    source_id : str
        Registry key the file was uploaded under, e.g. ``"wind"``.
    series : SourceSeries
        The power trace, built from the file's ``power_W`` column.
    inputs : dict of str to list of float
        Any recognised driving-input columns found in the file, keyed by
        :data:`~hybridharvest.sources.INPUTS` name.
    time : list of float
        Timestamps in seconds, from the file's ``time_s`` column.
    dt : float
        Timestep in seconds, inferred from the ``time_s`` column.
    filename : str
        Original upload name, shown back to the user.
    """

    source_id: str
    series: SourceSeries
    inputs: Dict[str, List[float]]
    time: List[float]
    dt: float
    filename: str

    def energy_wh(self) -> float:
        """Return the energy in the uploaded trace, in watt-hours."""
        return self.series.total_energy_wh(self.dt)

    def cumulative_energy_wh(self) -> List[float]:
        """Return the running energy total, one value per sample."""
        out: List[float] = []
        running = 0.0
        for power in self.series.power:
            running += power * self.dt / 3600.0
            out.append(running)
        return out

    def to_frame(self) -> pd.DataFrame:
        """Return the dataset in the ``data/processed`` CSV schema.

        Returns
        -------
        pandas.DataFrame
            ``time_s``, this source's input columns, ``power_W`` and
            ``energy_Wh_cumulative`` — the same shape
            ``scripts/export_categorized_data.py`` writes, so an uploaded file
            can be downloaded and re-uploaded unchanged.
        """
        frame = pd.DataFrame({"time_s": self.time})
        for name, values in self.inputs.items():
            frame[name] = values
        frame["power_W"] = self.series.power
        frame["energy_Wh_cumulative"] = self.cumulative_energy_wh()
        return frame


def category_from_csv(df: pd.DataFrame, source_id: str, filename: str) -> CategoryData:
    """Build a :class:`CategoryData` from an uploaded per-category CSV.

    Parameters
    ----------
    df : pandas.DataFrame
        Frame with at least ``time_s`` and ``power_W`` numeric columns.
    source_id : str
        Registry key the file is being uploaded as.
    filename : str
        Original upload name, kept for display.

    Returns
    -------
    CategoryData
        The parsed dataset, with ``dt`` inferred from ``time_s`` so a
        downsampled file reports its own effective timestep.

    Raises
    ------
    ValueError
        If ``time_s`` or ``power_W`` is missing, non-numeric, or too short to
        infer a timestep from.
    """
    required = ["time_s", "power_W"]
    missing = [name for name in required if name not in df.columns]
    if missing:
        raise ValueError(
            "missing required column(s): " + ", ".join(f"`{m}`" for m in missing)
        )

    for name in required:
        if not pd.api.types.is_numeric_dtype(df[name]):
            raise ValueError(f"column `{name}` must be numeric")

    if len(df) < 2:
        raise ValueError("need at least 2 rows to infer a timestep")

    times = df["time_s"].astype(float).tolist()
    dt = times[1] - times[0]
    if dt <= 0:
        raise ValueError(f"`time_s` must increase; got dt = {dt}")

    meta = SOURCES[source_id]
    inputs = {
        name: df[name].astype(float).tolist()
        for name in INPUTS[source_id]
        if name in df.columns
    }

    return CategoryData(
        source_id=source_id,
        series=SourceSeries(
            id=source_id,
            label=meta["label"],
            icon=meta["icon"],
            power=df["power_W"].astype(float).tolist(),
        ),
        inputs=inputs,
        time=times,
        dt=dt,
        filename=filename,
    )


@st.cache_data(show_spinner=False, max_entries=8)
def run_cached(
    hours: float,
    dt: float,
    seed: int,
    enable_solar: bool,
    piezo_config: str,
    piezo_elements: int,
    capacitance: float,
):
    """Run the simulation, memoised on the parameter tuple.

    A 24 h run at ``dt = 1 s`` is 86,400 steps and takes about a minute, which
    is long enough that a re-run triggered by an unrelated widget would look
    like a hang — especially on a small cloud instance. Caching means repeat
    runs with identical parameters return instantly.

    Parameters
    ----------
    hours, dt, seed, enable_solar, piezo_config, piezo_elements, capacitance
        Forwarded verbatim to
        :func:`~hybridharvest.simulation.run_simulation`. They form the cache
        key, so any change produces a fresh run.

    Returns
    -------
    SimulationResult
        The completed run.
    """
    return run_simulation(
        duration_hours=hours,
        dt=dt,
        seed=seed,
        enable_solar=enable_solar,
        piezo_config=piezo_config,
        piezo_elements=piezo_elements,
        capacitance=capacitance,
    )


# ---------------------------------------------------------------------------
# Sidebar — parameters
# ---------------------------------------------------------------------------
st.sidebar.title("⚡ HybridHarvest")
st.sidebar.caption(f"v{__version__}")
st.sidebar.header("Simulation parameters")

hours = st.sidebar.slider(
    "Duration (hours)", min_value=1, max_value=168, value=24,
    help="Simulated time span. 24 h = 86,400 steps at dt = 1 s.",
)
dt = st.sidebar.selectbox(
    "Timestep dt (s)", [0.5, 1.0, 2.0], index=1,
    help="Smaller steps are more accurate but proportionally slower.",
)
seed = st.sidebar.number_input(
    "Random seed", value=42, step=1,
    help="Fixes the weather/vibration generator. Same seed = same run.",
)

st.sidebar.divider()
st.sidebar.subheader("Source configuration")
piezo_config = st.sidebar.selectbox(
    "Piezo configuration", ["parallel", "series", "single"], index=0,
    help="Wiring of the piezoelectric array: parallel = 0.50, series = 0.45, "
         "single = 0.35.",
)
piezo_elements = st.sidebar.number_input(
    "Piezo elements", min_value=1, max_value=16, value=4, step=1,
    help="Number of elements in the piezo array.",
)
enable_solar = st.sidebar.checkbox(
    "Enable solar PV", value=False,
    help="Adds a fifth source: a 0.1 m² panel at 18 % efficiency on a "
         "diurnal irradiance curve.",
)

st.sidebar.divider()
st.sidebar.subheader("Storage")
capacitance = st.sidebar.number_input(
    "Capacitance (F)", min_value=0.1, max_value=1000.0, value=10.0, step=1.0,
    help="Supercapacitor capacitance. E = 0.5 · C · V².",
)

st.sidebar.divider()
out_dir = st.sidebar.text_input(
    "Output directory", value="output",
    help="Where the CSV is written when a run finishes.",
)
use_example = st.sidebar.checkbox(
    "Use example data", value=False,
    help="Load the checked-in 24 h example run instead of simulating.",
)
write_pngs = st.sidebar.checkbox(
    "Also write PNG plots", value=False,
    help="Off by default. Generating the ten matplotlib figures costs about "
         "45 s on a 24 h run and the dashboard never displays them — it draws "
         "with Plotly. Turn this on only if you want the files on disk; "
         "scripts/run_simulation.py and scripts/generate_example_report.py "
         "already produce them for reports.",
)
run_clicked = st.sidebar.button("▶ Run simulation", type="primary")

st.sidebar.divider()
steps = int(hours * 3600 / dt)
st.sidebar.caption(f"≈ {steps:,} timesteps per run")
if steps > 200_000:
    st.sidebar.warning("Large run — may take a while in the browser.")

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if run_clicked:
    if use_example:
        if os.path.exists(EXAMPLE_CSV):
            st.session_state["run"] = run_from_csv(pd.read_csv(EXAMPLE_CSV))
            st.session_state["meta"] = {
                "hours": hours, "dt": dt, "seed": seed,
                "csv": EXAMPLE_CSV, "example": True,
            }
        else:
            st.sidebar.error(f"Example data not found: {EXAMPLE_CSV}")
    else:
        status = st.status(f"Simulating {hours} h at dt={dt} s…", expanded=False)
        with status:
            st.write(f"{steps:,} timesteps — a 24 h run takes roughly a minute.")
            result = run_cached(
                hours=float(hours),
                dt=float(dt),
                seed=int(seed),
                enable_solar=enable_solar,
                piezo_config=piezo_config,
                piezo_elements=int(piezo_elements),
                capacitance=float(capacitance),
            )

            # Artifact writing is a convenience, not the product. On a hosted
            # container the filesystem is ephemeral and may be read-only, so a
            # failure here must not take the whole run down with it.
            csv_path = os.path.join(out_dir, "csv", "simulation.csv")
            wrote_artifacts = True
            try:
                os.makedirs(os.path.dirname(csv_path), exist_ok=True)
                save_csv(result, csv_path)
                if write_pngs:
                    with st.spinner("Writing PNG plots…"):
                        plots_dir = os.path.join(out_dir, "plots")
                        plot_results(result, plots_dir)
                        plot_all_source_details(result, plots_dir)
            except OSError as exc:
                wrote_artifacts = False
                st.warning(
                    f"Ran successfully, but the CSV/plots could not be written "
                    f"to `{out_dir}/` ({exc}). Everything below still works; "
                    "use the download button to save the data."
                )

            st.session_state["run"] = run_from_result(result, dt)
            st.session_state["meta"] = {
                "hours": hours, "dt": dt, "seed": seed,
                "csv": csv_path, "example": False,
                "wrote_artifacts": wrote_artifacts,
                "wrote_pngs": write_pngs,
            }
        status.update(label=f"Simulated {hours} h in {steps:,} steps", state="complete")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_sim, tab_upload, tab_help, tab_about = st.tabs(
    ["📊 Simulation", "📤 Upload Data", "📖 Help & Usage", "ℹ️ About"]
)

# --- Simulation tab --------------------------------------------------------
with tab_sim:
    st.title("HybridHarvest Energy Simulation")

    st.markdown(
        "Set your parameters in the sidebar and press **▶ Run simulation**.\n\n"
        "Each renewable source is reported separately so you can see its "
        "contribution to the total harvested energy.\n\n"
        "New here? Open the **📖 Help & Usage** tab for a full walkthrough."
    )

    run: RunData | None = st.session_state.get("run")
    meta = st.session_state.get("meta")

    if run is None:
        st.info("No run loaded yet.")
    else:
        # Charts are drawn from a decimated copy of the run. A 24 h run is
        # 86,400 samples per source; handing that many points to Plotly costs
        # roughly a minute of browser time to draw — far more than the
        # simulation itself (under a second) — and no screen can resolve it.
        # Every statistic below is still computed at full resolution.
        stride = max(1, len(run.time) // MAX_PLOT_POINTS)
        idx = range(0, len(run.time), stride)

        df = pd.DataFrame({"time_s": [run.time[i] for i in idx]})
        df["time_h"] = df["time_s"] / 3600.0
        for sid, series in run.sources.items():
            df[series.label] = [series.power[i] for i in idx]
        label_to_id = {s.label: sid for sid, s in run.sources.items()}

        src_wh = run.source_energy_wh()
        total_wh = run.total_energy_wh()
        load_wh = run.load_energy_wh()

        origin = "example data" if meta.get("example") else "simulation"
        st.caption(
            f"{len(run.time):,} steps · dt = {run.dt} s · {origin} · "
            f"{'seed ' + str(meta['seed']) if not meta.get('example') else 'fixed example run'}"
            + (f" · charts show every {stride}th sample" if stride > 1 else "")
        )

        # -- Per-source contribution --------------------------------------
        st.subheader("Per-Source Contribution")
        st.caption(
            "Pre-conversion energy per source. Shares are relative to the "
            "sum of all sources, so they add to 100 %."
        )
        cols = st.columns(len(run.sources))
        for col, (sid, series) in zip(cols, run.sources.items()):
            col.metric(
                label=f"{series.icon} {series.label}",
                value=f"{series.total_energy_wh(run.dt):,.3f} Wh",
                delta=f"{series.share_pct(src_wh, run.dt):.1f} % of total",
                delta_color="off",
            )

        # -- System totals ------------------------------------------------
        st.subheader("System Totals")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Harvested (after losses)", f"{total_wh:,.2f} Wh")
        c2.metric("Load consumed", f"{load_wh:,.4f} Wh")
        c3.metric("Net", f"{total_wh - load_wh:,.2f} Wh")
        c4.metric("Peak power", f"{max(run.total_power):,.2f} W")
        st.caption(
            f"Conversion efficiency 0.85: source energies sum to {src_wh:,.2f} Wh, "
            f"delivered as {total_wh:,.2f} Wh."
        )

        # -- Per-source detail --------------------------------------------
        st.subheader("Per-Source Detail")
        for sid, series in run.sources.items():
            with st.expander(f"{series.icon} {series.label}", expanded=False):
                st.plotly_chart(
                    px.line(
                        df, x="time_h", y=series.label,
                        labels={series.label: f"Power ({series.unit})",
                                "time_h": "Time (h)"},
                        color_discrete_sequence=["#4C78A8"],
                    ),
                    width='stretch',
                )
                d1, d2, d3 = st.columns(3)
                d1.metric("Peak", f"{series.peak_power():,.4f} W")
                d2.metric("Mean", f"{series.mean_power():,.4f} W")
                d3.metric("Energy", f"{series.total_energy_wh(run.dt):,.4f} Wh")

        # -- Aggregated views ---------------------------------------------
        st.subheader("Aggregated View")
        st.plotly_chart(
            px.area(
                df, x="time_h", y=list(label_to_id),
                labels={"value": "Power (W)", "time_h": "Time (h)",
                        "variable": "Source"},
                color_discrete_sequence=px.colors.qualitative.Set2,
            ),
            width='stretch',
        )

        agg = pd.DataFrame({
            "time_h": df["time_h"],
            "Harvested (after conversion)": [run.total_power[i] for i in idx],
            "Load": [run.load_power[i] for i in idx],
        })
        st.plotly_chart(
            px.line(
                agg, x="time_h",
                y=["Harvested (after conversion)", "Load"],
                labels={"value": "Power (W)", "time_h": "Time (h)",
                        "variable": "Series"},
            ),
            width='stretch',
        )

        storage_df = pd.DataFrame({
            "time_h": df["time_h"],
            "Voltage (V)": [run.storage_voltage[i] for i in idx],
            "State of charge": [run.soc[i] for i in idx],
        })
        st.plotly_chart(
            px.line(
                storage_df, x="time_h", y=["Voltage (V)", "State of charge"],
                labels={"value": "Value", "time_h": "Time (h)",
                        "variable": "Metric"},
            ),
            width='stretch',
        )

        # -- Per-source statistics table ----------------------------------
        with st.expander("Per-source summary statistics", expanded=False):
            stats = pd.DataFrame(
                {
                    "Peak (W)": {s.label: s.peak_power() for s in run.sources.values()},
                    "Mean (W)": {s.label: s.mean_power() for s in run.sources.values()},
                    "Energy (Wh)": {
                        s.label: s.total_energy_wh(run.dt)
                        for s in run.sources.values()
                    },
                    "Share (%)": {
                        s.label: s.share_pct(src_wh, run.dt)
                        for s in run.sources.values()
                    },
                }
            )
            stats.loc["Total"] = stats.sum()
            st.dataframe(stats.style.format("{:,.4f}"))

        # -- Download ------------------------------------------------------
        # Built from the full-resolution series, not the decimated chart frame:
        # the charts are downsampled for drawing speed, but a download is data
        # and losing samples silently would be wrong. Same schema save_csv
        # writes, so the file can be fed back in via "Use example data".
        export = pd.DataFrame({"time_s": run.time})
        for sid, series in run.sources.items():
            export[f"{sid}_W"] = series.power
        export["total_W"] = run.total_power
        export["storage_V"] = run.storage_voltage
        export["soc"] = run.soc
        export["load_W"] = run.load_power
        st.download_button(
            "⬇ Download CSV",
            data=export.to_csv(index=False).encode(),
            file_name="hybridharvest_simulation.csv",
            mime="text/csv",
            help=f"Full resolution — all {len(run.time):,} steps, "
                 "not the decimated chart data.",
        )
        if meta.get("example"):
            st.caption(f"Rendering the checked-in example run at `{meta['csv']}`.")
        elif not meta.get("wrote_artifacts", True):
            st.caption(
                "Artifacts were not written to disk on this host — download the "
                "CSV above to keep the run."
            )
        elif meta.get("wrote_pngs"):
            st.caption(
                f"Artifacts written to `{meta['csv']}` and `{out_dir}/plots/`."
            )
        else:
            st.caption(
                f"CSV written to `{meta['csv']}`. PNG plots were skipped — tick "
                "**Also write PNG plots** in the sidebar to generate them."
            )

# --- Help & Usage tab ------------------------------------------------------
with tab_help:
    st.title("📖 Help & Usage")


    st.markdown(
        """
        ### What this is
        HybridHarvest is a modular simulation framework for a **hybrid renewable
        energy harvesting** system. Several independent sources feed one energy
        manager, which charges a supercapacitor that powers a duty-cycled IoT
        load. Everything runs locally and deterministically — no network calls
        are made.
        """
    )

    st.markdown("### Quick start")
    st.markdown(
        """
        1. Set **Duration**, **Timestep** and **Seed** in the left sidebar.
        2. Optionally enable **Solar PV** or change the **piezo configuration**.
        3. Press **▶ Run simulation**.
        4. Read the per-source metrics and expanders, or download the CSV.
        """
    )

    st.markdown("### Source categories")
    st.markdown(
        """
        Every source is tracked, plotted and exported as its own category:

        | Icon | Source | Physical model | Governing relation |
        |---|---|---|---|
        | 🌬️ | **Wind Turbine** | Horizontal-axis turbine, Betz-limited | `P = 0.5 · ρ · A · v³ · Cp` |
        | 💧 | **Hydro Turbine** | Micro-hydro turbine | `P = ρ · g · Q · H · η` |
        | 📳 | **Vibration Harvester** | Resonant cantilever | `P = m · ζe · A² · ωn³ / (ζm + ζe)²` |
        | ⚡ | **Piezoelectric Array** | Array, single/series/parallel | `P = P_vib · η_config · n_elements` |
        | ☀️ | **Solar PV** (optional) | Photovoltaic panel | `P = G · A · η` |

        The internal class for hydro is still ``WaterTurbine`` — only the
        display name changed, so nothing downstream breaks.
        """
    )

    st.markdown("### Parameters")
    st.markdown(
        """
        | Parameter | Meaning | Guidance |
        |---|---|---|
        | Duration (hours) | Simulated time span | 1 h is quick; 24 h shows the full solar day; 168 h is one week |
        | Timestep dt (s) | Seconds advanced per step | 1.0 s is the default. Halving dt doubles runtime and accuracy |
        | Random seed | Seeds the weather/vibration generator | Same seed always reproduces the same run |
        | Piezo configuration | Array wiring | `parallel = 0.50`, `series = 0.45`, `single = 0.35` |
        | Piezo elements | Elements in the array | Power scales linearly with element count |
        | Enable solar PV | Adds the fifth source | Off by default; needs ≥ 6 h of run time to leave the night |
        | Capacitance (F) | Supercapacitor size | `E = 0.5 · C · V²`, voltage clamped to 5.5 V |
        | Use example data | Loads the checked-in 24 h run | Renders instantly, no simulation |
        """
    )

    st.markdown("### Reading the charts")
    st.markdown(
        """
        - **Per-Source Contribution** — one metric per source: its energy in Wh
          and its share of the total. Shares always add to 100 %.
        - **System Totals** — the aggregate after the 0.85 conversion
          efficiency is applied, alongside load and peak power.
        - **Per-Source Detail** — expand any source for its own time series and
          its peak / mean / energy. This is where you inspect a source that is
          too small to see in the stacked chart.
        - **Aggregated View** — stacked area of every source, total vs load, and
          the storage voltage + state of charge. A flat `soc` at 1.0 means the
          capacitor is saturated.
        """
    )

    st.markdown("### Two things that are easy to misread")
    st.markdown(
        """
        1. **Per-source values are pre-conversion; the total is post-conversion.**
           The four source series are summed at 100 %, then multiplied by the
           0.85 converter efficiency to give *Harvested (after losses)*. The
           per-source energies therefore will *not* add up to the total — that
           gap is the conversion loss, and the caption under **System Totals**
           shows both numbers.
        2. **The sources are not the same size.** A 0.6 m diameter wind turbine
           peaks near 31 W while the vibration harvester peaks near 34 mW, so
           wind dominates the stacked view. That is a property of the modelled
           hardware, not a bug — use the per-source expanders to see the small
           contributors clearly.
        """
    )

    st.markdown("### Tips")
    st.markdown(
        """
        - Start with **1 hour** to check a change, then scale up.
        - Keep the **seed fixed** when comparing parameter changes; vary it only
          when you want to sample different conditions.
        - Enable **solar** and run 24 h to see the diurnal curve; anything
          shorter than ~6 h starts at midnight and stays dark.
        - Runs are fully reproducible: same seed + same parameters = same CSV.
        """
    )

    st.markdown("### Troubleshooting")
    st.markdown(
        """
        | Symptom | Likely cause / fix |
        |---|---|
        | Page spins and never loads | Hard-refresh (`Cmd+Shift+R`). Confirm the URL is exactly `http://localhost:8501` |
        | `ModuleNotFoundError: hybridharvest` | Install from the repo root: `pip install -e ".[dev,ui]"` |
        | Simulation feels slow | Increase `dt`, or shorten the duration |
        | Solar column is all zeros | Run is shorter than 6 h (starts at midnight) or starts inside the night |
        | Storage chart is a flat line | Harvest greatly exceeds load — the capacitor is saturated |
        | Downloads are empty | Re-run; the download button renders from the current in-memory run |
        """
    )

    st.markdown("### Glossary")
    st.markdown(
        """
        | Term | Meaning |
        |---|---|
        | **SoC** | State of charge, 0 (empty) → 1 (full) |
        | **Cp** | Power coefficient; the Betz limit is 0.593 |
        | **Cut-in / rated** | Wind speeds below/above which the turbine produces nothing |
        | **Duty cycle** | Repeating pattern of load states |
        | **η (eta)** | Efficiency factor, always < 1 |
        | **Irradiance** | Solar power per unit area, W/m² |
        """
    )

    st.divider()
    st.caption(
        f"HybridHarvest v{__version__} · MIT License · "
        "see README.md for full documentation."
    )

# --- Upload Data tab ------------------------------------------------------
with tab_upload:
    st.title("📤 Upload Data")

    st.markdown(
        """
        Bring your own measurements in. Pick a category, drop in a CSV, and the
        dashboard validates the schema, plots the series and computes the same
        statistics the export script writes — then keeps it alongside the other
        categories for comparison.
        """
    )

    # -- Category + file ------------------------------------------------------
    pick_col, example_col = st.columns([3, 1])

    with pick_col:
        category = st.selectbox(
            "Data category",
            options=list(SOURCES),
            format_func=lambda sid: f"{SOURCES[sid]['icon']} {SOURCES[sid]['label']}",
            help="Which harvester this file belongs to.",
        )
    meta = SOURCES[category]

    example_csv = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data", "processed",
        category, f"example_{category}_24h.csv",
    )
    with example_col:
        st.write("")  # align the button with the selectbox
        load_example = st.button(
            "Load checked-in example",
            help=f"Loads data/processed/{category}/example_{category}_24h.csv",
        )

    uploaded_file = st.file_uploader(
        f"{meta['icon']} {meta['label']} CSV",
        type=["csv"],
        help="Needs `time_s` and `power_W`; the input columns are optional but "
             "unlock the extra statistics.",
    )

    # -- Resolve the file to parse -------------------------------------------
    incoming = None
    if load_example:
        if os.path.exists(example_csv):
            incoming = (pd.read_csv(example_csv), f"example_{category}_24h.csv")
        else:
            st.error(
                f"No checked-in example at `{example_csv}`. Run "
                "`python scripts/export_categorized_data.py` first."
            )
    elif uploaded_file is not None:
        try:
            incoming = (pd.read_csv(uploaded_file), uploaded_file.name)
        except Exception as exc:  # malformed CSV, wrong delimiter, ...
            st.error(f"Could not read `{uploaded_file.name}` as CSV: {exc}")

    # -- Parse, report, plot --------------------------------------------------
    if incoming is not None:
        raw, filename = incoming
        try:
            data = category_from_csv(raw, category, filename)
        except ValueError as exc:
            st.error(f"**{filename}** does not match the schema: {exc}")
            st.caption(
                "Required columns are `time_s` (numeric, increasing) and "
                "`power_W` (numeric)."
            )
        else:
            missing_inputs = [
                name for name in INPUTS[category] if name not in data.inputs
            ]
            st.success(
                f"Loaded **{filename}** — {len(data.time):,} rows at "
                f"dt = {data.dt:g} s ({len(data.time) * data.dt / 3600.0:.2f} h)."
            )
            if missing_inputs:
                st.warning(
                    "Missing expected input column(s): "
                    + ", ".join(f"`{n}`" for n in missing_inputs)
                    + ". The power statistics below are unaffected, but the "
                    "source-specific extras are unavailable."
                )

            with st.expander("Preview", expanded=False):
                st.dataframe(data.to_frame().head(20), width='stretch')

            st.subheader(f"{meta['icon']} {meta['label']} Power")
            st.plotly_chart(
                px.line(
                    pd.DataFrame(
                        {
                            "Time (h)": [t / 3600.0 for t in data.time],
                            f"Power ({data.series.unit})": data.series.power,
                        }
                    ),
                    x="Time (h)",
                    y=f"Power ({data.series.unit})",
                    color_discrete_sequence=["#4C78A8"],
                ),
                width='stretch',
            )

            st.subheader("Statistics")
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Peak", f"{data.series.peak_power():,.4f} W")
            s2.metric("Mean", f"{data.series.mean_power():,.4f} W")
            s3.metric("Energy", f"{data.energy_wh():,.4f} Wh")
            s4.metric(
                "Capacity factor",
                f"{data.series.mean_power() / data.series.peak_power():.4f}"
                if data.series.peak_power() > 0
                else "—",
            )

            if data.inputs:
                st.markdown("**Driving inputs** (mean / min / max)")
                input_rows = []
                for name, values in data.inputs.items():
                    input_rows.append(
                        {
                            "Input": name,
                            "Description": INPUTS[category][name],
                            "Mean": f"{sum(values) / len(values):.6f}",
                            "Min": f"{min(values):.6f}",
                            "Max": f"{max(values):.6f}",
                        }
                    )
                st.dataframe(
                    pd.DataFrame(input_rows), hide_index=True,
                    width='stretch',
                )

            st.download_button(
                f"⬇ Download normalised {category} CSV",
                data=data.to_frame().to_csv(index=False).encode(),
                file_name=f"processed_{category}_{filename}",
                mime="text/csv",
                help="Same schema as data/processed/, so it re-uploads unchanged.",
            )

            keep = st.checkbox(
                "Keep for comparison",
                value=st.session_state.get("keep_uploads", False),
                key="keep_uploads",
                help="Adds this category to the comparison view below. Kept in "
                     "session state only; nothing is written to disk.",
            )
            uploads = st.session_state.setdefault("uploads", {})
            if keep:
                uploads[category] = data
            elif category in uploads:
                del uploads[category]

    else:
        st.info("Upload a CSV above, or load the checked-in example.")
        with st.expander("Expected CSV format", expanded=False):
            st.markdown(
                f"""
                For **{meta['label']}** (`{category}`):

                | Column | Required | Meaning |
                |---|---|---|
                | `time_s` | yes | Time in seconds, increasing |
                | `power_W` | yes | Instantaneous power in Watts |
                """
                + "".join(
                    f"| `{name}` | no | {desc} |\n"
                    for name, desc in INPUTS[category].items()
                )
                + """
                | `energy_Wh_cumulative` | no | Running total in Wh |

                A plain two-column `time_s,power_W` file works. The tab also
                accepts the whole-system `output/csv/simulation.csv` shape by
                reading the matching `<category>_W` column.
                """
            )

    # -- Comparison with other uploaded / example categories ------------------
    uploads = st.session_state.get("uploads", {})
    if uploads:
        st.divider()
        st.subheader("Comparison")

        if len(uploads) == 1:
            only = next(iter(uploads.values()))
            st.info(
                f"One category saved ({only.series.label}). Tick **Keep for "
                "comparison** on a second category to see them stacked."
            )
        else:
            reference = next(iter(uploads.values())).time
            aligned = all(
                len(d.time) == len(reference)
                and all(abs(a - b) < 1e-9 for a, b in zip(d.time, reference))
                for d in uploads.values()
            )

            if aligned:
                compare = pd.DataFrame({"Time (h)": [t / 3600.0 for t in reference]})
                for sid, d in uploads.items():
                    compare[f"{SOURCES[sid]['icon']} {d.series.label}"] = d.series.power

                st.caption(
                    "All saved categories share a time base, so they can be "
                    "stacked directly."
                )
                st.plotly_chart(
                    px.area(
                        compare,
                        x="Time (h)",
                        y=[c for c in compare.columns if c != "Time (h)"],
                        labels={"value": "Power (W)", "variable": "Source"},
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    ),
                    width='stretch',
                )
            else:
                st.warning(
                    "Saved categories have different time bases or lengths, so "
                    "they cannot be stacked. Per-category totals below."
                )

            totals = [
                {
                    "Source": f"{SOURCES[sid]['icon']} {d.series.label}",
                    "Energy (Wh)": d.energy_wh(),
                }
                for sid, d in uploads.items()
            ]
            st.plotly_chart(
                px.bar(
                    pd.DataFrame(totals),
                    x="Source",
                    y="Energy (Wh)",
                    color="Source",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                ),
                width='stretch',
            )

            summary = pd.DataFrame(
                {
                    d.series.label: {
                        "Rows": len(d.time),
                        "dt (s)": d.dt,
                        "Duration (h)": round(len(d.time) * d.dt / 3600.0, 4),
                        "Peak (W)": round(d.series.peak_power(), 6),
                        "Mean (W)": round(d.series.mean_power(), 6),
                        "Energy (Wh)": round(d.energy_wh(), 6),
                    }
                    for d in uploads.values()
                }
            )
            st.dataframe(summary, width='stretch')

        if st.button("Clear saved uploads"):
            st.session_state["uploads"] = {}
            st.session_state["keep_uploads"] = False
            st.rerun()

# --- About tab -------------------------------------------------------------
with tab_about:
    st.title("ℹ️ About HybridHarvest")

    st.markdown(
        f"""
        **Version** {__version__} · MIT License

        A modular simulation and control framework for hybrid renewable energy
        harvesting. Four sources are always simulated, a fifth (solar) is
        opt-in, and every source is reported as its own category in the UI,
        the CSV export and the plots.
        """
    )

    st.markdown("### Architecture")
    st.markdown(
        """
        | Layer | Module | Responsibility |
        |---|---|---|
        | Sources | `wind_model`, `water_model`, `vibration_model`, `piezo_model`, `solar_model` | One class per harvester, all subclassing `EnergySource` |
        | Registry | `sources` | `SOURCES` metadata + `SourceSeries` statistics |
        | Control | `energy_manager` | Aggregation and conversion losses |
        | Storage | `storage_model` | Supercapacitor charge / discharge and clamping |
        | Load | `load_model` | Duty-cycled IoT device model |
        | Orchestration | `simulation` | The time-stepping loop, `SimulationResult`, `save_csv` |
        | Reporting | `reporting` | Aggregate and per-source matplotlib figures |
        """
    )

    st.markdown("### Reproducing the example run")
    st.code(
        "pip install -e \".[dev,ui]\"\n"
        "python scripts/run_simulation.py --hours 24 --solar --out output/\n"
        "python scripts/generate_example_report.py\n"
        "pytest -q",
        language="bash",
    )

    st.markdown("### Adding a new source")
    st.markdown(
        """
        Add one entry to `SOURCES` in `src/hybridharvest/sources.py`, write the
        model class, and both the dashboard and the CSV pick it up
        automatically — no other file needs to change.
        """
    )

    st.divider()
    st.caption("Built with pandas, matplotlib, plotly and streamlit.")
