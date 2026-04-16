"""PID controller for pan and tilt axes.

This module implements a standard PID controller with anti-windup clamping.
The algorithm is unchanged from the original prototype; this refactor adds full
type hints, Google-style docstrings, and replaces the magic-number integral
clamp with a constructor parameter.
"""

import time


class PIDController:
    """Discrete-time PID controller with anti-windup integral clamping.

    Example:
        >>> pid = PIDController(kp=3.0, ki=0.0, kd=0.1, max_out=1500.0)
        >>> velocity = pid.update(error_pixels)

    Attributes:
        kp: Proportional gain.
        ki: Integral gain.
        kd: Derivative gain.
        max_out: Output magnitude clamp in steps/sec.
        max_integral: Anti-windup clamp for the raw integral accumulator.
    """

    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        max_out: float = 2000.0,
        max_integral: float = 500.0,
    ) -> None:
        """Initialise the PID controller.

        Args:
            kp: Proportional gain — speed contribution per unit of error.
            ki: Integral gain — accumulates steady-state error over time.
            kd: Derivative gain — damping term that opposes rapid changes.
            max_out: Maximum absolute output value in steps/sec.
            max_integral: Anti-windup clamp applied to the raw integral
                accumulator before the ``ki`` multiplier.  Replaces the
                original magic number ``500``.
        """
        self.kp: float = kp
        self.ki: float = ki
        self.kd: float = kd
        self.max_out: float = max_out
        self.max_integral: float = max_integral

        self._prev_error: float = 0.0
        self._integral: float = 0.0
        self._prev_d: float = 0.0
        self._last_time: float = time.monotonic()

    def update(self, error: float) -> float:
        """Compute the PID output for the given error signal.

        Args:
            error: Signed error in the same units as the system being
                controlled (e.g. pixels for camera tracking).

        Returns:
            Signed output value clamped to ``[-max_out, +max_out]``.
        """
        current_time = time.monotonic()
        dt = current_time - self._last_time

        # Prevent divide-by-zero when called faster than clock resolution.
        if dt <= 0.0:
            return 0.0

        # 1. Proportional term.
        p_term = self.kp * error

        # 2. Integral term with anti-windup clamping.
        self._integral += error * dt
        self._integral = max(min(self._integral, self.max_integral), -self.max_integral)
        i_term = self.ki * self._integral

        # 3. Derivative term with low-pass filter.
        delta_error = error - self._prev_error
        d_term = self.kd * (delta_error / dt)
        d_term = 0.1 * d_term + 0.9 * self._prev_d
        self._prev_d = d_term

        # Compute output and clamp to motor limits.
        output = p_term + i_term + d_term
        output = max(min(output, self.max_out), -self.max_out)

        # Update state for next call.
        self._prev_error = error
        self._last_time = current_time

        return output

    def reset(self) -> None:
        """Reset all internal state.

        Call this when a target is lost or when the controller should start
        fresh (e.g. on FSM transition back to SCAN).
        """
        self._prev_error = 0.0
        self._integral = 0.0
        self._prev_d = 0.0
        self._last_time = time.monotonic()
