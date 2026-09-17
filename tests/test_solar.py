import pytest

from hybridharvest.solar_model import SolarPanel


def test_name_is_solar():
    assert SolarPanel().name == "solar"


def test_power_is_zero_before_any_step():
    assert SolarPanel().power() == 0.0


def test_step_with_irradiance():
    panel = SolarPanel(area=0.1, eta=0.18)
    assert panel.step(1.0, irradiance=1000.0) == pytest.approx(18.0)


def test_negative_irradiance_is_clamped_to_zero():
    panel = SolarPanel(area=0.1, eta=0.18)
    assert panel.step(1.0, irradiance=-50.0) == 0.0


def test_step_without_irradiance_holds_previous_state():
    panel = SolarPanel(area=0.1, eta=0.18)
    panel.step(1.0, irradiance=500.0)
    assert panel.step(1.0) == pytest.approx(9.0)


def test_power_scales_with_area_and_efficiency():
    small = SolarPanel(area=0.05, eta=0.18)
    large = SolarPanel(area=0.10, eta=0.18)
    assert large.step(1.0, irradiance=1000.0) == pytest.approx(
        2 * small.step(1.0, irradiance=1000.0)
    )
