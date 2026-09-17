from hybridharvest.load_model import IoTLoad, LoadState


def test_sleep_phase():
    l = IoTLoad()
    assert l.step(1.0, time_in_cycle=10.0) == LoadState.SLEEP.value


def test_sensing_phase():
    l = IoTLoad()
    assert l.step(1.0, time_in_cycle=56.0) == LoadState.SENSING.value


def test_transmit_phase():
    l = IoTLoad()
    assert l.step(1.0, time_in_cycle=59.0) == LoadState.TRANSMIT.value


def test_cycle_wraps():
    l = IoTLoad()
    assert l.step(1.0, time_in_cycle=70.0) == LoadState.SLEEP.value