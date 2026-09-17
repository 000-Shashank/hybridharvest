import pytest
from hybridharvest.water_model import WaterTurbine


def test_zero_flow():
    t = WaterTurbine()
    assert t.step(1.0, flow=0.0) == 0.0


def test_power_scales_linearly():
    t = WaterTurbine()
    p1 = t.step(1.0, flow=1.0)
    p2 = t.step(1.0, flow=2.0)
    assert p2 == pytest.approx(2 * p1, rel=1e-9)


def test_positive_power():
    t = WaterTurbine()
    assert t.step(1.0, flow=2.5) > 0


def test_state_persists():
    t = WaterTurbine()
    t.step(1.0, flow=3.0)
    assert t.power() == t.power()