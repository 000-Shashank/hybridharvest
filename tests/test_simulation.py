import csv

import pytest

from hybridharvest.simulation import SimulationResult, run_simulation, save_csv

CORE = {"wind", "hydro", "vibration", "piezo"}
FULL_HEADER = [
    "time_s", "wind_W", "hydro_W", "vibration_W",
    "piezo_W", "solar_W", "total_W", "storage_V", "soc", "load_W",
]


def test_core_sources_are_always_simulated():
    result = run_simulation(duration_hours=0.01, dt=1.0, seed=1)
    assert set(result.sources) == CORE


def test_solar_is_opt_in():
    assert "solar" not in run_simulation(
        duration_hours=0.01, dt=1.0, seed=1
    ).sources
    assert "solar" in run_simulation(
        duration_hours=0.01, dt=1.0, seed=1, enable_solar=True
    ).sources


def test_every_series_has_one_sample_per_step():
    result = run_simulation(duration_hours=0.05, dt=1.0, seed=7, enable_solar=True)
    steps = len(result.time)
    assert steps == 180
    for series in result.sources.values():
        assert len(series.power) == steps
    assert len(result.total_power) == steps
    assert len(result.storage_voltage) == steps
    assert len(result.soc) == steps
    assert len(result.load_power) == steps


def test_backwards_compatible_properties():
    result = run_simulation(duration_hours=0.01, dt=1.0, seed=1)
    assert result.wind_power == result.sources["wind"].power
    assert result.hydro_power == result.sources["hydro"].power
    assert result.water_power == result.sources["hydro"].power  # legacy alias
    assert result.vibration_power == result.sources["vibration"].power
    assert result.piezo_power == result.sources["piezo"].power
    assert result.solar_power == []


def test_empty_result_properties_are_safe():
    result = SimulationResult()
    assert result.wind_power == []
    assert result.hydro_power == []
    assert result.water_power == []
    assert result.vibration_power == []
    assert result.piezo_power == []
    assert result.solar_power == []
    assert result.total_energy_wh(1.0) == 0.0
    assert result.source_energy_wh(1.0) == 0.0


def test_runs_are_deterministic_for_a_fixed_seed():
    a = run_simulation(duration_hours=0.05, dt=1.0, seed=3)
    b = run_simulation(duration_hours=0.05, dt=1.0, seed=3)
    assert a.wind_power == b.wind_power
    assert a.total_power == b.total_power


def test_different_seeds_diverge():
    a = run_simulation(duration_hours=0.05, dt=1.0, seed=1)
    b = run_simulation(duration_hours=0.05, dt=1.0, seed=2)
    assert a.wind_power != b.wind_power


def test_vibration_power_is_milliwatt_scale():
    """Regression: amplitude is a displacement in metres.

    Sampling 0.1-1.0 m from a 10 g cantilever produced megawatts, because
    power scales with amplitude squared.
    """
    result = run_simulation(duration_hours=1.0, dt=1.0, seed=42)
    assert result.sources["vibration"].peak_power() < 1.0


def test_total_energy_is_source_energy_after_conversion_losses():
    result = run_simulation(duration_hours=0.5, dt=1.0, seed=5)
    assert result.total_energy_wh(1.0) == pytest.approx(
        result.source_energy_wh(1.0) * 0.85
    )


def test_shares_sum_to_one_hundred_over_a_full_run():
    result = run_simulation(duration_hours=1.0, dt=1.0, seed=42, enable_solar=True)
    total = result.source_energy_wh(1.0)
    shares = sum(s.share_pct(total, 1.0) for s in result.sources.values())
    assert shares == pytest.approx(100.0)


def test_storage_voltage_stays_within_bounds():
    result = run_simulation(duration_hours=1.0, dt=1.0, seed=42)
    assert min(result.storage_voltage) >= 0.0
    assert max(result.storage_voltage) <= 5.5 + 1e-9
    assert all(0.0 <= s <= 1.0 for s in result.soc)


def test_solar_follows_the_diurnal_curve():
    result = run_simulation(duration_hours=24.0, dt=60.0, seed=1, enable_solar=True)
    solar = result.sources["solar"].power
    # Starts at midnight: dark, then bright around noon.
    assert solar[0] == 0.0
    noon_index = int(12 * 3600 / 60)
    assert solar[noon_index] > 0.0
    assert solar[noon_index] == max(solar)


def test_csv_header_has_one_column_per_source(tmp_path):
    result = run_simulation(duration_hours=0.01, dt=1.0, seed=1, enable_solar=True)
    path = tmp_path / "sim.csv"
    save_csv(result, str(path))
    with open(path, newline="", encoding="utf-8") as handle:
        assert next(csv.reader(handle)) == FULL_HEADER


def test_csv_omits_solar_when_it_was_not_simulated(tmp_path):
    result = run_simulation(duration_hours=0.01, dt=1.0, seed=1)
    path = tmp_path / "sim.csv"
    save_csv(result, str(path))
    with open(path, newline="", encoding="utf-8") as handle:
        assert "solar_W" not in next(csv.reader(handle))


def test_csv_row_count_matches_step_count(tmp_path):
    result = run_simulation(duration_hours=0.01, dt=1.0, seed=1)
    path = tmp_path / "sim.csv"
    save_csv(result, str(path))
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert len(rows) == len(result.time) + 1


def test_csv_values_match_the_result(tmp_path):
    result = run_simulation(duration_hours=0.01, dt=1.0, seed=1)
    path = tmp_path / "sim.csv"
    save_csv(result, str(path))
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert float(rows[0]["wind_W"]) == pytest.approx(result.wind_power[0])
    assert float(rows[-1]["total_W"]) == pytest.approx(result.total_power[-1])
