import time

class PIDController:
    def __init__(self, kp, ki, kd, max_out=2000):
        """
        kp: Proportional Gain (Speed per pixel error)
        ki: Integral Gain (Overcomes steady-state error)
        kd: Derivative Gain (Damping to prevent overshoot)
        max_out: Maximum output speed (steps/sec)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_out = max_out
        
        self._prev_error = 0
        self._integral = 0
        self._last_time = time.time()
        
    def update(self, error):
        current_time = time.time()
        dt = current_time - self._last_time
        
        # Prevent divide by zero if called too fast
        if dt <= 0.0:
            return 0.0

        # 1. Proportional Term
        p_term = self.kp * error

        # 2. Integral Term (Accumulates error over time)
        self._integral += error * dt
        # Clamp Integral (Anti-Windup) - prevents it from growing infinitely
        # A simple clamp to +/- 500 speed contribution is usually safe
        self._integral = max(min(self._integral, 500), -500)
        i_term = self.ki * self._integral

        # 3. Derivative Term (Rate of change of error)
        delta_error = error - self._prev_error
        d_term = self.kd * (delta_error / dt)

        # Calculate Output
        output = p_term + i_term + d_term

        # Clamp Total Output to Motor Limits
        output = max(min(output, self.max_out), -self.max_out)

        # Update state for next loop
        self._prev_error = error
        self._last_time = current_time

        return output

    def reset(self):
        """Reset history when target is lost"""
        self._prev_error = 0
        self._integral = 0
        self._last_time = time.time()