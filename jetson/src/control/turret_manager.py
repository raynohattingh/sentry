# src/control/turret_manager.py
from control.pid import PIDController
from hardware.arduino_link import ArduinoLink
import config

class TurretManager:
    def __init__(self):
        self.hardware = ArduinoLink()
        self.pan_pid = PIDController(config.PAN_KP, config.PAN_KI, config.PAN_KD, config.PAN_MAX)
        self.tilt_pid = PIDController(config.TILT_KP, config.TILT_KI, config.TILT_KD, config.TILT_MAX)

    def track(self, target_data):
        """
        Receives target dictionary: {"cx": int, "cy": int, ...}
        Calculates PID output and moves motors.
        """
        if target_data:
            # 1. Calculate Error
            err_x = target_data["cx"] - config.CENTER_X
            err_y = target_data["cy"] - config.CENTER_Y

            # 2. Dead Zone Check
            if abs(err_x) < config.DEAD_ZONE: err_x = 0
            if abs(err_y) < config.DEAD_ZONE: err_y = 0

            # 3. Update PIDs
            # NOTE: Invert these signs if motors move wrong way!
            v_pan = self.pan_pid.update(err_x)
            v_tilt = self.tilt_pid.update(err_y)

            # 4. Move
            self.hardware.send_velocity(v_pan, v_tilt)
            
            return err_x, v_pan # Return for telemetry/debug overlay
        
        else:
            # No Target -> Stop and Reset
            self.stop()
            return 0, 0

    def stop(self):
        self.hardware.send_velocity(0, 0)
        self.pan_pid.reset()
        self.tilt_pid.reset()