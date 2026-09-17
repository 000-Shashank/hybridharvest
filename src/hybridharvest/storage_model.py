"""Supercapacitor storage model."""
from __future__ import annotations


class Supercapacitor:
    """Ideal supercapacitor with voltage clamping.

    E = 0.5 * C * V^2

    Parameters
    ----------
    capacitance : float
        Capacitance in Farads.
    v_max : float
        Maximum (fully charged) voltage in Volts.
    v_min : float
        Minimum (empty) voltage in Volts.
    """

    def __init__(
        self, capacitance: float, v_max: float, v_min: float = 0.0
    ) -> None:
        if v_max <= v_min:
            raise ValueError("v_max must be > v_min")
        self.C = capacitance
        self.v_max = v_max
        self.v_min = v_min
        self.voltage = v_min

    def energy(self) -> float:
        """Return stored energy in Joules.

        Returns
        -------
        float
            Energy in Joules.
        """
        return 0.5 * self.C * self.voltage ** 2

    def _set_energy(self, energy: float) -> None:
        """Clamp energy to the safe window and update the voltage."""
        e_min = 0.5 * self.C * self.v_min ** 2
        e_max = 0.5 * self.C * self.v_max ** 2
        energy = max(e_min, min(e_max, energy))
        self.voltage = (2 * energy / self.C) ** 0.5

    def charge(self, power: float, dt: float, efficiency: float = 0.92) -> float:
        """Charge the capacitor with a constant power for ``dt`` seconds.

        Parameters
        ----------
        power : float
            Charging power in Watts.
        dt : float
            Duration in seconds.
        efficiency : float, optional
            Charging efficiency.

        Returns
        -------
        float
            Energy actually stored, in Joules (zero for non-positive power).
        """
        if power <= 0:
            return 0.0
        before = self.energy()
        self._set_energy(before + power * dt * efficiency)
        return self.energy() - before

    def discharge(self, power: float, dt: float) -> float:
        """Discharge the capacitor at a constant power for ``dt`` seconds.

        Parameters
        ----------
        power : float
            Discharge power in Watts.
        dt : float
            Duration in seconds.

        Returns
        -------
        float
            Energy actually delivered, in Joules (zero for non-positive power).
        """
        if power <= 0:
            return 0.0
        before = self.energy()
        self._set_energy(before - power * dt)
        return before - self.energy()

    def soc(self) -> float:
        """Return the state of charge in the range ``[0, 1]``.

        Returns
        -------
        float
            Fraction of usable energy currently stored.
        """
        e_min = 0.5 * self.C * self.v_min ** 2
        e_max = 0.5 * self.C * self.v_max ** 2
        if e_max == e_min:
            return 0.0
        return (self.energy() - e_min) / (e_max - e_min)