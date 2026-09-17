from hybridharvest.energy_manager import EnergyManager
from hybridharvest.base import EnergySource


class FakeSource(EnergySource):
    def __init__(self, name, value):
        super().__init__(name)
        self.value = value

    def power(self):
        return self.value

    def step(self, dt, **kwargs):
        return self.value


def test_total_power_sums():
    m = EnergyManager(sources=[FakeSource("a", 1.0), FakeSource("b", 2.0)])
    assert m.total_power() == 3.0 * 0.85


def test_net_power_negative():
    m = EnergyManager(sources=[FakeSource("a", 0.1)])
    assert m.net_power(load_power=10.0) < 0


def test_step_returns_dict():
    m = EnergyManager(sources=[FakeSource("a", 1.0)])
    out = m.step(1.0)
    assert "per_source" in out and "total" in out