import pytest
from hybridharvest.wind_model import WindTurbine


def test_zero_below_cut_in():
    t = WindTurbine()
    assert t.step(1.0, wind_speed=1.5) == 0.0
    assert t.step(1.0, wind_speed=0.0) == 0.0


def test_power_scales_with_cube():
    t = WindTurbine()
    p1 = t.step(1.0, wind_speed=5.0)
    p2 = t.step(1.0, wind_speed=10.0)
    assert p2 == pytest.approx(p1 * 8, rel=1e-6)


def test_above_rated_returns_zero():
    t = WindTurbine()
    assert t.step(1.0, wind_speed=15.0) == 0.0


def test_step_updates_state():
    t = WindTurbine()
    t.step(1.0, wind_speed=6.0)
    assert t.wind_speed == 6.0
    assert t.power() > 0


def test_nan_rejected():
    t = WindTurbine()
    with pytest.raises(ValueError):
        t.step(1.0, wind_speed=float("nan"))