import pytest
from hybridharvest.storage_model import Supercapacitor


def test_energy_formula():
    c = Supercapacitor(capacitance=10.0, v_max=5.0)
    c.voltage = 3.0
    assert c.energy() == pytest.approx(0.5 * 10.0 * 9.0)


def test_overvoltage_protection():
    c = Supercapacitor(capacitance=10.0, v_max=5.5)
    for _ in range(1000):
        c.charge(power=100.0, dt=1.0)
    assert c.voltage <= 5.5 + 1e-6


def test_undervoltage_clamp():
    c = Supercapacitor(capacitance=10.0, v_max=5.5, v_min=2.0)
    c.voltage = 3.0
    c.discharge(power=1000.0, dt=1.0)
    assert c.voltage >= 2.0 - 1e-6


def test_soc_bounds():
    c = Supercapacitor(capacitance=10.0, v_max=5.5)
    assert c.soc() == pytest.approx(0.0)
    for _ in range(1000):
        c.charge(power=100.0, dt=1.0)
    assert c.soc() == pytest.approx(1.0, abs=1e-6)