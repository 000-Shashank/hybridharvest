import pytest
from hybridharvest.piezo_model import PiezoArray


def test_single_config():
    p = PiezoArray(config="single")
    assert p.step(1.0, vib_power=1.0) == pytest.approx(0.35)


def test_series_config():
    p = PiezoArray(config="series")
    assert p.step(1.0, vib_power=1.0) == pytest.approx(0.45)


def test_parallel_config():
    p = PiezoArray(config="parallel")
    assert p.step(1.0, vib_power=1.0) == pytest.approx(0.50)


def test_array_multiplies():
    p = PiezoArray(config="parallel", n_elements=4)
    assert p.step(1.0, vib_power=1.0) == pytest.approx(2.0)


def test_invalid_config():
    with pytest.raises(ValueError):
        PiezoArray(config="bogus")