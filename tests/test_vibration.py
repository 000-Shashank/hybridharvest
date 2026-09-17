from hybridharvest.vibration_model import VibrationHarvester


def test_zero_amplitude():
    v = VibrationHarvester()
    assert v.step(1.0, freq=50, amp=0.0) == 0.0


def test_positive_power():
    v = VibrationHarvester()
    assert v.step(1.0, freq=50, amp=0.5) > 0


def test_power_scales_with_amp_squared():
    v = VibrationHarvester()
    p1 = v.step(1.0, freq=50, amp=0.5)
    p2 = v.step(1.0, freq=50, amp=1.0)
    assert p2 == 4 * p1


def test_state_persists():
    v = VibrationHarvester()
    v.step(1.0, freq=50, amp=0.5)
    assert v.power() > 0