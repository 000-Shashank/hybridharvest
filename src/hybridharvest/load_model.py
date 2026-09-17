"""IoT load model with duty cycle."""
from __future__ import annotations
from enum import Enum


class LoadState(Enum):
    SLEEP = 0.005
    SENSING = 0.080
    TRANSMIT = 0.250


class IoTLoad:
    """ESP32-class IoT load with 60 s duty cycle.

    Cycle: 0-54 s SLEEP, 54-58.8 s SENSING, 58.8-60 s TRANSMIT.
    """

    def __init__(self) -> None:
        self.state = LoadState.SLEEP

    def power(self) -> float:
        """Return instantaneous power in Watts.

        Returns
        -------
        float
            Power in Watts according to the current state.
        """
        return self.state.value

    def step(self, dt: float, time_in_cycle: float) -> float:
        """Advance the load state based on time in the duty cycle.

        Parameters
        ----------
        dt : float
            Timestep duration in seconds. The load model is quasi-static.
        time_in_cycle : float
            Time in seconds within the 60-second duty cycle.

        Returns
        -------
        float
            Power in Watts after the update.
        """
        phase = time_in_cycle % 60.0
        if phase < 54.0:
            self.state = LoadState.SLEEP
        elif phase < 58.8:
            self.state = LoadState.SENSING
        else:
            self.state = LoadState.TRANSMIT
        return self.power()