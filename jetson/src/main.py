"""Sentry Jetson Core — main control loop.

Entry point for the autonomous thermal sentry turret brain.

Architecture:
    ThreadedCamera → ObjectDetector → CentroidTracker → ThreatScorer
    → SentryBrain (FSM) → ArduinoLink → TelemetryRecorder → MQTTPublisher
    Flask MJPEG web stream runs in a daemon thread.

Performance target: ≥ 20 Hz main loop; ≤ 100 ms frame-to-serial-command latency.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import threading
import time
import uuid

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Bootstrap: sys.path must include this directory.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import config
from sentry_types import FSMState, TurretPosition

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Boot failure counter (FR-030)
# ---------------------------------------------------------------------------


def _read_boot_state() -> dict:
    try:
        with open(config.BOOT_STATE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"consecutive_failures": 0, "last_failure_utc": None}


def _write_boot_state(state: dict) -> None:
    os.makedirs(os.path.dirname(config.BOOT_STATE_PATH) or ".", exist_ok=True)
    with open(config.BOOT_STATE_PATH, "w") as f:
        json.dump(state, f)


def _check_boot_failures() -> None:
    state = _read_boot_state()
    failures = state.get("consecutive_failures", 0)
    if failures >= config.MAX_BOOT_FAILURES:
        logger.critical(
            "[SYSTEM] %d consecutive boot failures — triggering OS reboot.", failures
        )
        os.system("sudo reboot")  # noqa: S605
        sys.exit(1)


def _reset_boot_failures() -> None:
    _write_boot_state({"consecutive_failures": 0, "last_failure_utc": None})


def _increment_boot_failures() -> None:
    state = _read_boot_state()
    state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
    state["last_failure_utc"] = datetime.datetime.utcnow().isoformat() + "Z"
    _write_boot_state(state)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the sentry control loop."""
    logger.info("[SYSTEM] Sentry Core starting up…")

    # Boot failure guard.
    _check_boot_failures()

    # Session ID — UUID4, immutable for the lifetime of this process.
    session_id = str(uuid.uuid4())
    logger.info("[SYSTEM] Session ID: %s", session_id)

    # --- Initialise subsystems ---

    # AI / Vision
    try:
        from vision.camera import ThreadedCamera
        from vision.detector import ObjectDetector
        from vision.tracker import CentroidTracker

        camera = ThreadedCamera().start()
        detector = ObjectDetector()
        tracker = CentroidTracker()
    except (RuntimeError, AssertionError, FileNotFoundError) as exc:
        logger.critical("[SYSTEM] FATAL — TensorRT inference failed to initialise: %s", exc)
        _increment_boot_failures()
        sys.exit(1)

    # Control
    from control.sentry_brain import SentryBrain
    from control.threat_tracker import ThreatScorer

    brain = SentryBrain()
    scorer = ThreatScorer()

    # Hardware
    from hardware.arduino_link import ArduinoLink

    link = ArduinoLink()
    link.connect()

    # PID controllers (owned here for direct error injection from camera)
    from control.pid import PIDController

    pan_pid = PIDController(config.PAN_KP, config.PAN_KI, config.PAN_KD, config.PAN_MAX,
                             config.PID_MAX_INTEGRAL)
    tilt_pid = PIDController(config.TILT_KP, config.TILT_KI, config.TILT_KD, config.TILT_MAX,
                              config.PID_MAX_INTEGRAL)

    # Comms / Telemetry
    from comms.mqtt import MQTTPublisher
    from telemetry.recorder import TelemetryRecorder

    mqtt_pub = MQTTPublisher()
    recorder = TelemetryRecorder(session_id=session_id, mqtt=mqtt_pub)

    # Web HUD
    from web.streamer import start_web_server, update_stream_frame

    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()

    # Boot counter reset — we reached the main loop successfully.
    _reset_boot_failures()
    logger.info("[SYSTEM] Sentry Core Online.")

    # ---------------------------------------------------------------------------
    # Control loop
    # ---------------------------------------------------------------------------
    loop_count = 0
    loop_times: list[float] = []

    try:
        while True:
            loop_start = time.monotonic()

            # A. Capture frame.
            frame = camera.read()
            if frame is None:
                time.sleep(0.005)
                continue

            raw = frame.data

            # B. Detect targets.
            detections = detector.detect(raw)

            # C. Track targets.
            targets = tracker.update(detections)

            # D. Score threats.
            assessments = [
                scorer.score(t, targets, config.LRF_ENABLED) for t in targets
            ]

            # E. Get current turret position.
            position = link.current_position

            # F. Compute PID velocities for best target (if any).
            if targets and brain.state in (FSMState.TRACK, FSMState.ACQUIRE):
                best_target = max(targets, key=lambda t: t.area)
                err_x = best_target.centroid[0] - config.CENTER_X
                err_y = best_target.centroid[1] - config.CENTER_Y

                if abs(err_x) < config.DEAD_ZONE:
                    err_x = 0
                if abs(err_y) < config.DEAD_ZONE:
                    err_y = 0

                v_pan = pan_pid.update(float(err_x))
                v_tilt = tilt_pid.update(float(err_y))
            else:
                pan_pid.reset()
                tilt_pid.reset()
                v_pan, v_tilt = 0.0, 0.0

            # G. FSM update (returns scan/search velocities; TRACK/ACQUIRE uses PID above).
            command = brain.update(assessments, position)

            # Override FSM scan/search velocities with PID when tracking.
            if brain.state in (FSMState.TRACK, FSMState.ACQUIRE):
                final_pan = v_pan
                final_tilt = v_tilt
                fire_lrf = command.fire_lrf
            else:
                final_pan = command.pan_velocity
                final_tilt = command.tilt_velocity
                fire_lrf = command.fire_lrf

            # H. Send to Arduino.
            link.send_velocity(final_pan, final_tilt)
            if fire_lrf:
                link.fire_lrf()

            # I. Telemetry.
            for t in targets:
                a = next((x for x in assessments if x.target_id == t.target_id), None)
                if a:
                    rec = recorder.record(t, a, link.last_lrf_reading, position, fsm_state=brain.state)
                    recorder.emit(rec)

            # J. HUD overlay.
            display = raw.copy()
            for t in targets:
                x1, y1, x2, y2 = t.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 2)
                a = next((x for x in assessments if x.target_id == t.target_id), None)
                score_txt = f"{a.threat_score:.0f}" if a else "?"
                cv2.putText(display,
                            f"ID:{t.target_id} S:{score_txt}",
                            (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            state_color = (0, 255, 0)
            cv2.putText(display, f"FSM:{brain.state.value}",
                        (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, state_color, 2)

            if brain.approaching_limit:
                cv2.putText(display, "[TURRET] Approaching limit",
                            (8, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

            # Show loop FPS.
            if loop_times:
                fps = 1.0 / (sum(loop_times) / len(loop_times))
                cv2.putText(display, f"FPS:{fps:.1f}",
                            (8, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            update_stream_frame(display)

            # K. Performance tracking.
            loop_end = time.monotonic()
            loop_ms = (loop_end - loop_start) * 1000.0
            loop_times.append(loop_end - loop_start)
            if len(loop_times) > 100:
                loop_times.pop(0)

            loop_count += 1
            if loop_count % 100 == 0:
                avg_ms = sum(loop_times) / len(loop_times) * 1000
                fps = 1000.0 / avg_ms if avg_ms > 0 else 0
                logger.info("[PERF] loop_ms=%.1f fps=%.1f", avg_ms, fps)
                if fps < 18:
                    logger.warning("[SYSTEM] WARNING — loop rate degraded (%.1f Hz).", fps)

            if loop_ms > 100:
                logger.warning("[PERF] WARNING: loop exceeded 100 ms (%.1f ms)", loop_ms)

    except KeyboardInterrupt:
        logger.info("[SYSTEM] Keyboard interrupt — shutting down.")
    finally:
        link.stop()
        camera.stop()
        logger.info("[SYSTEM] Sentry Core shutdown complete.")


if __name__ == "__main__":
    main()
