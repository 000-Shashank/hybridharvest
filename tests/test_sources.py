import pytest

from hybridharvest.sources import (
    CORE_SOURCES,
    SOURCES,
    SourceSeries,
    make_series,
)


def test_registry_has_the_expected_sources():
    assert set(SOURCES) == {"wind", "hydro", "vibration", "piezo", "solar"}


def test_every_registry_entry_has_label_and_icon():
    for source_id, meta in SOURCES.items():
        assert meta["label"], f"{source_id} is missing a label"
        assert meta["icon"], f"{source_id} is missing an icon"


def test_core_sources_are_a_subset_of_the_registry():
    assert set(CORE_SOURCES) <= set(SOURCES)
    assert "solar" not in CORE_SOURCES


def test_make_series_pulls_metadata_from_the_registry():
    series = make_series("hydro")
    assert series.id == "hydro"
    assert series.label == "Hydro Turbine"
    assert series.icon == SOURCES["hydro"]["icon"]
    assert series.unit == "W"
    assert series.power == []


def test_empty_series_reports_zero_stats():
    series = SourceSeries("wind", "Wind Turbine", "🌬️")
    assert series.peak_power() == 0.0
    assert series.mean_power() == 0.0
    assert series.total_energy_wh(1.0) == 0.0
    assert series.share_pct(0.0, 1.0) == 0.0


def test_stats_math():
    series = SourceSeries("wind", "Wind Turbine", "🌬️", power=[1.0, 2.0, 3.0])
    assert series.peak_power() == 3.0
    assert series.mean_power() == pytest.approx(2.0)
    # 6 W of samples at dt=3600 s is 6 Wh.
    assert series.total_energy_wh(3600.0) == pytest.approx(6.0)


def test_shares_sum_to_one_hundred():
    wind = SourceSeries("wind", "Wind Turbine", "🌬️", power=[1.0, 1.0])
    hydro = SourceSeries("hydro", "Hydro Turbine", "💧", power=[3.0, 3.0])
    total = wind.total_energy_wh(1.0) + hydro.total_energy_wh(1.0)
    assert wind.share_pct(total, 1.0) == pytest.approx(25.0)
    assert hydro.share_pct(total, 1.0) == pytest.approx(75.0)


def test_share_pct_uses_the_supplied_dt():
    """A share must be independent of the timestep used to compute it."""
    wind = SourceSeries("wind", "Wind Turbine", "🌬️", power=[2.0])
    hydro = SourceSeries("hydro", "Hydro Turbine", "💧", power=[6.0])
    for dt in (0.5, 1.0, 2.0):
        total = wind.total_energy_wh(dt) + hydro.total_energy_wh(dt)
        assert wind.share_pct(total, dt) == pytest.approx(25.0)
