============================================================================
                            HYBRIDHARVEST
        Modular Simulation & Control Framework for Hybrid Renewable
                    Energy Harvesting Systems
================================================================================

Version:      0.1.0
Language:     Python 3.11+
License:      MIT
Repository:   https://github.com/000-Shashank/hybridharvest
Dashboard:    app/dashboard.py  (deploy per README.md, section "Deployment")

--------------------------------------------------------------------------------
OVERVIEW
--------------------------------------------------------------------------------

HybridHarvest is a modular Python framework for simulating, controlling, and
validating a hybrid renewable energy harvesting system that combines several
sources:

    - Wind       (horizontal-axis turbine, Betz-limited)
    - Hydro      (micro-hydro turbine; class name WaterTurbine)
    - Vibration  (resonant cantilever harvester)
    - Piezo      (piezoelectric array, single/series/parallel)
    - Solar      (photovoltaic panel, OPTIONAL - off by default)

Every source is tracked, plotted and exported as its OWN CATEGORY. The
dashboard shows a metric tile per source with its energy and percentage share,
one expandable chart per source, and the CSV carries one column per source
(wind_W, hydro_W, vibration_W, piezo_W, solar_W). See the PER-SOURCE
REPORTING section below.

The harvested energy is managed by a central EnergyManager, stored in a
supercapacitor, and consumed by an IoT load (ESP32-class, duty-cycled). The
system is designed to simulate first, validate with automated tests, and then
transition to real hardware without changing the control architecture.

An optional, API-key-gated AI layer provides natural-language summaries and
fault explanations. Without an API key, a deterministic mock backend runs —
no network calls are ever made.

--------------------------------------------------------------------------------
FEATURES
--------------------------------------------------------------------------------

  [x] Five physical harvesting models (wind, hydro, vibration, piezo, solar)
  [x] Per-source categorization: separate metrics, charts and CSV columns
  [x] Central SOURCES registry - add a source with one dict entry
  [x] Energy manager with conversion + storage efficiency
  [x] Supercapacitor storage model with voltage clamping
  [x] IoT load model with 60-second duty cycle (SLEEP/SENSING/TRANSMIT)
  [x] 24-hour simulation loop with CSV logging
  [x] Automatic plot generation (aggregate + one PNG per source)
  [x] Checked-in example run + generated Markdown report
  [x] pytest suite with 85%+ coverage target
  [x] Hypothesis property-based tests
  [x] MATLAB cross-validation scripts
  [x] LaTeX technical report + auto-generated PDF
  [x] GitLab CI/CD pipeline (test, docs, report)
  [x] Optional AI layer (OpenAI / Anthropic), mock by default
  [x] Streamlit dashboard, deployable to Streamlit Community Cloud
  [x] Multi-key AI support (priority, round-robin, weighted, fallback)

--------------------------------------------------------------------------------
REQUIREMENTS
--------------------------------------------------------------------------------

  - Python 3.11 or newer
  - pip (bundled with Python)
  - Optional: MATLAB (for cross-validation only)
  - Optional: LaTeX (for PDF report generation)
  - Optional: An OpenAI or Anthropic API key (for live AI features)

--------------------------------------------------------------------------------
INSTALLATION
--------------------------------------------------------------------------------

1. Clone the repository:

       git clone https://github.com/000-Shashank/hybridharvest.git
       cd hybridharvest

2. Create and activate a virtual environment:

   On Linux/macOS:

       python3 -m venv .venv
       source .venv/bin/activate

   On Windows:

       python -m venv .venv
       .venv\Scripts\activate

3. Install the package with development extras:

       pip install -e ".[dev]"

4. (Optional) Install AI extras:

       pip install -e ".[ai]"

5. (Optional) Install UI extras:

       pip install -e ".[ui]"

--------------------------------------------------------------------------------
QUICKSTART
--------------------------------------------------------------------------------

Run a 24-hour simulation and generate CSV + plots:

    python scripts/run_simulation.py --hours 24 --out output/

Expected output:

    [ok] steps: 86400
    [ok] total harvested: X.XXXX Wh
    [ok] csv: output/csv/simulation.csv
    [ok] plots: output/plots

Run the test suite:

    pytest

Run the test suite with coverage:

    pytest --cov=hybridharvest --cov-report=term --cov-fail-under=85

Launch the Streamlit dashboard:

    streamlit run app/dashboard.py

--------------------------------------------------------------------------------
COMMAND-LINE INTERFACE
--------------------------------------------------------------------------------

scripts/run_simulation.py

    Usage:

        python scripts/run_simulation.py [OPTIONS]

    Options:

        --hours FLOAT     Simulation duration in hours (default: 24.0)
        --dt FLOAT        Timestep in seconds (default: 1.0)
        --seed INT        Random seed (default: 42)
        --out PATH        Output directory (default: output)
        --solar           Include the optional solar PV source
        --piezo-config {single,series,parallel}
                          Piezoelectric array wiring (default: parallel)
        --piezo-elements INT
                          Number of piezo elements (default: 4)
        --ai              Enable AI summarization (requires AI_API_KEY)
        --help            Show help message

    Examples:

        python scripts/run_simulation.py --hours 1
        python scripts/run_simulation.py --hours 24 --solar
        python scripts/run_simulation.py --hours 48 --dt 0.5 --seed 123
        python scripts/run_simulation.py --hours 24 --out results/ --solar

    The run prints a per-source contribution table:

        [ok] per-source contribution:
               source            peak (W)    mean (W)   energy (Wh)    share
               wind               31.0337      7.7274      185.4571   61.52%
               hydro               0.5886      0.2943        7.0642    2.34%
               vibration           0.0345      0.0128        0.3066    0.10%
               piezo               0.0689      0.0255        0.6131    0.20%
               solar              18.0000      4.5000      108.0000   35.83%
        [ok] total harvested (after conversion): 256.2240 Wh

--------------------------------------------------------------------------------
PROJECT STRUCTURE
--------------------------------------------------------------------------------

    hybridharvest/
    |
    +-- README.md                  Markdown readme (this file)
    +-- README.txt                 Full ASCII documentation
    +-- pyproject.toml             Package metadata + build config
    +-- requirements.txt           Core dependencies (Streamlit Cloud reads this)
    +-- .streamlit/config.toml     Streamlit theme + server settings
    +-- src/hybridharvest/         Source package
    |   +-- __init__.py
    |   +-- base.py                EnergySource abstract class
    |   +-- sources.py             SOURCES registry + SourceSeries statistics
    |   +-- wind_model.py          WindTurbine
    |   +-- water_model.py         WaterTurbine  (displayed as "Hydro")
    |   +-- vibration_model.py     VibrationHarvester
    |   +-- piezo_model.py         PiezoArray
    |   +-- solar_model.py         SolarPanel (optional)
    |   +-- energy_manager.py      EnergyManager
    |   +-- storage_model.py       Supercapacitor
    |   +-- load_model.py          IoTLoad
    |   +-- simulation.py          run_simulation, SimulationResult, save_csv
    |   +-- reporting.py           Aggregate + per-source figures
    |
    +-- tests/                     pytest suite
    |   +-- conftest.py
    |   +-- test_wind.py
    |   +-- test_water.py          <-- still named water for import compatibility
    |   +-- test_vibration.py
    |   +-- test_piezo.py
    |   +-- test_solar.py
    |   +-- test_energy_manager.py
    |   +-- test_storage.py
    |   +-- test_load.py
    |   +-- test_simulation.py
    |
    +-- scripts/
    |   +-- run_simulation.py
    |   +-- generate_example_report.py
    |
    +-- app/                       Streamlit dashboard
    |   +-- dashboard.py
    |
    +-- examples/
    |   +-- example_report.md      Generated 24 h run report
    |   +-- data/                  example_simulation.csv
    |   +-- plots/                 One PNG per source + aggregate charts
    |
    +-- docs/                      Optional LaTeX report (unchanged)
    |   +-- report.tex
    |   +-- user_guide.tex
    |   +-- ai_optional.md
    |   +-- figures/
    |
    +-- data/                      Runtime dirs (unchanged)
    |   +-- raw/
    |   +-- processed/
    |
    +-- models/                    Trained AI model weights (optional)
    |
    +-- output/                    Runtime dirs (unchanged)
        +-- csv/                   Simulation CSV output
        +-- plots/                 Generated PNG plots
        +-- reports/               Generated PDF reports

--------------------------------------------------------------------------------
ARCHITECTURE
--------------------------------------------------------------------------------

    +-------------------------------------------------------------+
    |                    HYBRID ENERGY SYSTEM                     |
    +-------------------------------------------------------------+
                                |
            +-------------------+-------------------+
            |                   |                   |
            v                   v                   v
          WIND                WATER            VIBRATION
            |                   |                   |
            v                   v                   v
         Turbine             Turbine              Piezo
            |                   |                   |
            +-------------------+-------------------+
                                |
                                v
                        ENERGY MANAGER
                                |
                                v
                        STORAGE / BATTERY
                                |
                                v
                             ESP32
                                |
                                v
                          IoT SENSOR

    Optional AI layer wraps the EnergyManager for:
        - Power forecasting
        - Anomaly detection
        - Natural-language summaries
        - Fault explanations

--------------------------------------------------------------------------------
PHYSICAL MODELS
--------------------------------------------------------------------------------

  Wind:
      P = 0.5 * rho * A * v^3 * Cp
      Betz limit: Cp <= 0.593

  Hydro:
      P = rho * g * Q * H * eta

  Vibration (resonant cantilever):
      P = m * zeta_e * A^2 * omega_n^3 / (zeta_m + zeta_e)^2

  Piezoelectric array:
      P = P_vib * eta_config * n_elements
      eta: single=0.35, series=0.45, parallel=0.50

  Solar (optional):
      P = G * A * eta
      G = irradiance in W/m^2, diurnal curve peaking at local noon
      defaults: A = 0.1 m^2, eta = 0.18

  Storage:
      E = 0.5 * C * V^2

--------------------------------------------------------------------------------
OPTIONAL AI LAYER
--------------------------------------------------------------------------------

The AI layer is DISABLED BY DEFAULT and requires NO API KEY to run.

Without AI_API_KEY:
    - MockBackend runs
    - Deterministic output
    - No network calls
    - Safe for CI and offline use

With AI_API_KEY:
    - LLMBackend runs (OpenAI or Anthropic)
    - Natural-language simulation summaries
    - Fault explanations

Environment variables:

    AI_API_KEY        Your API key (enables live AI)
    AI_PROVIDER       "openai" or "anthropic" (default: mock)
    AI_MODEL          Model name (default: gpt-4o-mini or claude-3-5-sonnet)
    AI_KEYS_FILE      Path to multi-key JSON config (default: .ai_keys.json)
    AI_ROUTING_STRATEGY   "priority" | "round_robin" | "weighted" | "fallback"

Example (single key):

    export AI_PROVIDER=openai
    export AI_API_KEY=sk-...
    python scripts/run_simulation.py --hours 24 --ai

Example (multi-key via .ai_keys.json):

    {
      "providers": {
        "openai": {
          "keys": [
            { "id": "openai-1", "value": "sk-...", "priority": 1 },
            { "id": "openai-2", "value": "sk-...", "priority": 2 }
          ],
          "model": "gpt-4o-mini",
          "enabled": true
        },
        "anthropic": {
          "keys": [
            { "id": "anthropic-1", "value": "sk-ant-...", "priority": 1 }
          ],
          "model": "claude-3-5-sonnet",
          "enabled": true
        }
      },
      "routing": {
        "strategy": "priority",
        "fallback_chain": ["openai", "anthropic"],
        "max_retries_per_key": 2,
        "cooldown_seconds": 60
      }
    }

Then:

    export AI_KEYS_FILE=.ai_keys.json
    python scripts/run_simulation.py --hours 24 --ai

IMPORTANT:
    - .ai_keys.json is in .gitignore. NEVER commit it.
    - Key values are never logged. Only key IDs.
    - If all keys fail, the adapter falls back to MockBackend.

--------------------------------------------------------------------------------
STREAMLIT DASHBOARD
--------------------------------------------------------------------------------

Run locally:

    streamlit run app/dashboard.py

Deploy to Streamlit Community Cloud (free):

    1. Push the project to a public GitHub repository.
    2. Go to https://share.streamlit.io
    3. Click "New app".
    4. Select your repo, branch, and main file path: app/dashboard.py
    5. Click "Deploy".

Notes:
    - Public apps are free.
    - Apps sleep after 7 days of no traffic.
    - First access after sleep triggers a 30-60 second cold start.

--------------------------------------------------------------------------------
TESTING
--------------------------------------------------------------------------------

Run all tests:

    pytest

Run with coverage:

    pytest --cov=hybridharvest --cov-report=term --cov-fail-under=85

Run a single module's tests:

    pytest tests/test_wind.py -v

Run AI tests (mock mode, no key needed):

    pytest tests/ai/ -v

Run live AI tests (requires AI_API_KEY):

    AI_API_KEY=sk-... pytest tests/ai/test_llm_skipped.py -v

Property-based tests (Hypothesis):

    pytest tests/ -k property

--------------------------------------------------------------------------------
MATLAB CROSS-VALIDATION
--------------------------------------------------------------------------------

The matlab/ directory contains independent implementations of the wind,
water, and storage models.

To run the comparison:

    1. Generate Python simulation output:

           python scripts/run_simulation.py --hours 24 --out output/

    2. Open MATLAB and run:

           cd matlab
           compare_with_python

    3. The script will:
           - Load output/csv/simulation.csv
           - Recompute wind power in MATLAB
           - Compute RMSE against Python
           - Save output/plots/matlab_vs_python.png

Expected RMSE: < 0.1% of peak power.

--------------------------------------------------------------------------------
LATEX REPORT GENERATION
--------------------------------------------------------------------------------

Generate the technical report PDF:

    python scripts/generate_report.py

This will:
    1. Copy plots from output/plots/ to docs/figures/
    2. Run pdflatex twice on docs/report.tex
    3. Move the final PDF to output/reports/report.pdf

Requires a LaTeX installation (TeX Live, MiKTeX, or MacTeX).

--------------------------------------------------------------------------------
CI/CD PIPELINE
--------------------------------------------------------------------------------

The .gitlab-ci.yml pipeline has three stages:

    test     - Runs pytest with coverage gate (85%)
    docs     - Builds the LaTeX report
    report   - Runs a 24-hour simulation and generates the PDF report

All stages run WITHOUT an AI_API_KEY. The mock backend is exercised.

To enable live AI tests in CI, add AI_API_KEY as a masked CI/CD variable.

--------------------------------------------------------------------------------
TROUBLESHOOTING
--------------------------------------------------------------------------------

Problem: ModuleNotFoundError: No module named 'hybridharvest'

    Solution: Ensure you installed with `pip install -e .` from the
    project root.

Problem: pytest cannot find tests

    Solution: Run pytest from the project root, not from inside src/.
    The pyproject.toml sets testpaths = ["tests"].

Problem: matplotlib backend errors on headless systems

    Solution: reporting.py already sets matplotlib.use("Agg").
    If you still see errors, export MPLBACKEND=Agg.

Problem: Streamlit app shows "ModuleNotFoundError"

    Solution: Add a requirements.txt at the repo root (already present).
    Streamlit Cloud installs from it automatically.

Problem: AI features do not activate

    Solution: Check that AI_API_KEY is set AND AI_PROVIDER is valid.
    If the key is invalid, the adapter falls back to MockBackend silently.
    Set AI_DEBUG=1 to log which backend is active.

Problem: pdflatex not found

    Solution: Install TeX Live (Linux), MacTeX (macOS), or MiKTeX (Windows).
    Or skip the report stage — the simulation still works.

--------------------------------------------------------------------------------
ROADMAP
--------------------------------------------------------------------------------

    v0.1  Core simulation (wind, water, vibration, piezo)
    v0.2  Energy manager + storage + load
    v0.3  Simulation loop + CSV + plots
    v0.4  OOP refactor + full pytest suite
    v0.5  GitLab CI/CD
    v0.6  MATLAB cross-validation
    v0.7  LaTeX report + auto-generation
    v0.8  Optional AI layer (mock + LLM backends)
    v0.9  Multi-key AI routing
    v1.0  Streamlit dashboard + Streamlit Cloud deploy
    v1.1  ESP32 hardware integration (planned)

--------------------------------------------------------------------------------
CONTRIBUTING
--------------------------------------------------------------------------------

    1. Fork the repository.
    2. Create a feature branch:

           git checkout -b feature/my-feature

    3. Make changes, add tests, ensure coverage stays >= 85%.
    4. Run the full suite:

           pytest --cov=hybridharvest --cov-fail-under=85

    5. Commit with a conventional message:

           git commit -m "feat(wind): add cut-out speed handling"

    6. Push and open a merge request.

Commit types: feat, fix, test, docs, refactor, ci, chore.

--------------------------------------------------------------------------------
LICENSE
--------------------------------------------------------------------------------

MIT License

Copyright (c) 2026 shashank N

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

--------------------------------------------------------------------------------
CONTACT
--------------------------------------------------------------------------------

    Project maintainer: shashank N <134797738+000-Shashank@users.noreply.github.com>
    Issues:             https://github.com/000-Shashank/hybridharvest/issues
    Discussions:        https://github.com/000-Shashank/hybridharvest/discussions

================================================================================
                        END OF README
================================================================================