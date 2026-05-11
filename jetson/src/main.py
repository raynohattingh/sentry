"""Sentry Jetson Core — main control loop.

Entry point for the autonomous thermal sentry turret brain.

Architecture:
    ThreadedCamera → ObjectDetector → CentroidTracker → ThreatScorer
    → SentryBrain (FSM) → ArduinoLink → TelemetryRecorder → MQTTPublisher
    Flask MJPEG web stream runs in a daemon thread.

Performance target: ≥ 20 Hz main loop; ≤ 100 ms frame-to-serial-command latency.
"""

from __future__ import annotations

import collections
import datetime
import json
import logging
import os
import subprocess
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
        subprocess.run(["sudo", "reboot"], check=False)
        sys.exit(1)


def _reset_boot_failures() -> None:
    _write_boot_state({"consecutive_failures": 0, "last_failure_utc": None})


def _increment_boot_failures() -> None:
    state = _read_boot_state()
    state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
    state["last_failure_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
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
    try:
        from control.sentry_brain import SentryBrain
        from control.threat_tracker import ThreatScorer

        brain = SentryBrain()
        scorer = ThreatScorer()
    except Exception as exc:
        logger.critical("[SYSTEM] FATAL — Control subsystem init failed: %s", exc)
        _increment_boot_failures()
        sys.exit(1)

    # Hardware
    try:
        from hardware.arduino_link import ArduinoLink

        link = ArduinoLink()
        if not link.connect():
            raise RuntimeError(
                f"ArduinoLink.connect() returned False (port={config.SERIAL_PORT})"
            )

        from control.turret_manager import TurretManager

        turret = TurretManager(hardware=link)
        logger.info(
            "[SAFETY] Startup profile=%s validation_state=%s motion_allowed=%s",
            turret.housing_profile.value,
            turret.validation_state.value,
            turret.motion_allowed,
        )
        if turret.motion_block_reason is not None:
            logger.warning("[SAFETY] Motion blocked: %s", turret.motion_block_reason)
    except Exception as exc:
        logger.critical("[SYSTEM] FATAL — Hardware subsystem init failed: %s", exc)
        _increment_boot_failures()
        sys.exit(1)

    # Comms / Telemetry
    from comms.mqtt import CommandSubscriber, MQTTPublisher
    from telemetry.recorder import TelemetryRecorder

    mqtt_pub = MQTTPublisher()
    status_pub = MQTTPublisher(topic=config.MQTT_STATUS_TOPIC)
    recorder = TelemetryRecorder(session_id=session_id, mqtt=mqtt_pub)

    # Manual override command subscriber — listens on MQTT_COMMAND_TOPIC,
    # validates SENTRY_ID, rate-limits, and drives turret directly. The
    # safety watchdog stops motion if no command arrives within
    # COMMAND_SAFETY_TIMEOUT_S.
    command_sub = CommandSubscriber(
        set_velocity=turret.set_velocity,
        enter_override=brain.enter_override,
        exit_override=brain.exit_override,
    )
    command_sub.start()

    # Web HUD
    from web.streamer import start_web_server, update_stream_frame

    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()

    # Boot counter reset — we reached the main loop successfully.
    _reset_boot_failures()
    logger.info("[SYSTEM] Sentry Core Online.")

    last_safety_payload: str | None = None

    def publish_safety_status() -> None:
        nonlocal last_safety_payload
        payload = json.dumps(turret.get_safety_status().to_dict())
        if payload != last_safety_payload:
            status_pub.publish_async(payload)
            last_safety_payload = payload

    publish_safety_status()

    # ---------------------------------------------------------------------------
    # Control loop
    # ---------------------------------------------------------------------------
    loop_count = 0
    loop_times: collections.deque[float] = collections.deque(maxlen=100)
    consecutive_errors = 0

    try:
        while True:
          try:
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

            # F. Select best target by threat score (not area).
            best_centroid = None
            if targets and assessments:
                best_assessment = max(assessments, key=lambda a: a.threat_score)
                best_target = next(
                    (t for t in targets if t.target_id == best_assessment.target_id),
                    None,
                )
                if best_target is not None:
                    best_centroid = best_target.centroid

            # G. FSM update (SentryBrain owns all PID computation).
            command = brain.update(
                assessments,
                position,
                target_centroid=best_centroid,
                frame_center=(config.CENTER_X, config.CENTER_Y),
            )

            final_pan = command.pan_velocity
            final_tilt = command.tilt_velocity
            fire_lrf = command.fire_lrf

            # H. Send to Arduino.
            turret.set_velocity(final_pan, final_tilt)
            if fire_lrf:
                link.fire_lrf()
            publish_safety_status()

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

            loop_count += 1
            if loop_count % 100 == 0:
                avg_ms = sum(loop_times) / len(loop_times) * 1000
                fps = 1000.0 / avg_ms if avg_ms > 0 else 0
                logger.info("[PERF] loop_ms=%.1f fps=%.1f", avg_ms, fps)
                if fps < 18:
                    logger.warning("[SYSTEM] WARNING — loop rate degraded (%.1f Hz).", fps)

            if loop_ms > 100:
                logger.warning("[PERF] WARNING: loop exceeded 100 ms (%.1f ms)", loop_ms)

            consecutive_errors = 0

          except Exception as exc:
            consecutive_errors += 1
            logger.exception("[SYSTEM] Main loop error (#%d): %s", consecutive_errors, exc)
            if consecutive_errors >= 10:
                logger.critical("[SYSTEM] Too many consecutive errors — exiting.")
                _increment_boot_failures()
                break
            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("[SYSTEM] Keyboard interrupt — shutting down.")
    finally:
        link.stop()
        camera.stop()
        try:
            mqtt_pub.publish_async("")  # flush signal
        except Exception:
            pass
        logger.info("[SYSTEM] Sentry Core shutdown complete.")


if __name__ == "__main__":
    main()
