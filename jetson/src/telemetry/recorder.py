"""TelemetryRecorder — build, annotate, and emit TelemetryRecord objects.

Writes JSON-lines to a rotating file (via logging.handlers.RotatingFileHandler)
and publishes each record to MQTT asynchronously.  All records carry the
session_id injected at construction time.

Prefix: ``[TELEMETRY]``
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import logging
import logging.handlers
import math
import os
import time

import config
from comms.mqtt import MQTTProtocol
from control.geo import compute_target_gps, pan_tilt_to_azimuth
from sentry_types import (
    FSMState,
    LRFReading,
    ThreatAssessment,
    TelemetryRecord,
    TrackedTarget,
    TurretPosition,
)

logger = logging.getLogger(__name__)


def _convert_velocity(v_px_frame: float, lrf_m: float) -> float | None:
    """Convert pixel-per-frame velocity to metres per second.

    Uses the pinhole camera model:
        focal_px = (CAMERA_WIDTH / 2) / tan(HFOV / 2)
        v_m_s = (v_px_frame * lrf_m) / (focal_px * CAMERA_FPS)

    Args:
        v_px_frame: Velocity component in pixels per frame.
        lrf_m: Laser range-finder distance to target in metres.

    Returns:
        Velocity component in metres per second, or None if the result
        is not finite (e.g. NaN or infinity).
    """
    focal_px = (config.CAMERA_WIDTH / 2.0) / math.tan(
        math.radians(config.CAMERA_HFOV_DEG / 2.0)
    )
    result = (v_px_frame * lrf_m) / (focal_px * config.CAMERA_FPS)
    if not math.isfinite(result):
        return None
    return result


class TelemetryRecorder:
    """Build and emit TelemetryRecord snapshots.

    Example:
        >>> recorder = TelemetryRecorder(session_id="abc-123", mqtt=mqtt_pub)
        >>> record = recorder.record(target, assessment, lrf, position)
        >>> recorder.emit(record)

    Attributes:
        session_id: UUID4 string generated at process startup; immutable.
    """

    def __init__(self, session_id: str, mqtt: MQTTProtocol) -> None:
        """Initialise the recorder.

        Args:
            session_id: UUID4 string generated at process startup.
            mqtt: MQTTProtocol instance for asynchronous publishing.
        """
        self.session_id: str = session_id
        self._mqtt: MQTTProtocol = mqtt

        # Set up rotating JSON-lines log handler.
        log_path = config.TELEMETRY_LOG_PATH
        os.makedirs(os.path.dirname(log_path) if os.path.dirname(log_path) else ".", exist_ok=True)

        self._jsonl_logger = logging.getLogger(f"telemetry.jsonl.{session_id}")
        self._jsonl_logger.setLevel(logging.INFO)
        self._jsonl_logger.propagate = False  # don't send to root logger

        # Always close and replace handlers so that tests with different
        # tmp_path directories get a fresh file handle.
        for h in list(self._jsonl_logger.handlers):
            h.close()
            self._jsonl_logger.removeHandler(h)

        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=config.TELEMETRY_MAX_BYTES,
            backupCount=config.TELEMETRY_BACKUP_COUNT,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._jsonl_logger.addHandler(handler)

        self._mqtt_interval_s: float = 1.0 / max(1, config.TELEMETRY_MQTT_HZ)
        self._last_mqtt_publish: float = 0.0

        logger.info("[TELEMETRY] Recorder initialised; session=%s log=%s mqtt_hz=%d",
                    session_id, log_path, config.TELEMETRY_MQTT_HZ)

    def record(
        self,
        target: TrackedTarget,
        assessment: ThreatAssessment,
        lrf_reading: LRFReading | None,
        position: TurretPosition,
        fsm_state: FSMState = FSMState.SCAN,
    ) -> TelemetryRecord:
        """Build a TelemetryRecord from the current subsystem state.

        Args:
            target: The tracked target for this record.
            assessment: The corresponding threat assessment.
            lrf_reading: Latest LRF reading, or None if unavailable.
            position: Current turret position.
            fsm_state: Current FSM state from SentryBrain.

        Returns:
            A fully populated TelemetryRecord with nullable GPS fields.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

        # Compute pan/tilt angles.
        pan_angle = position.pan_steps / config.STEPS_PER_DEGREE
        tilt_angle = position.tilt_steps / config.STEPS_PER_DEGREE

        # Compute GPS coordinates if LRF is enabled and reading is valid.
        lat: float | None = None
        lon: float | None = None
        lrf_distance: float | None = None
        velocity_vector: dict | None = None

        if config.LRF_ENABLED and lrf_reading and lrf_reading.valid and lrf_reading.distance_m is not None:
            lrf_distance = lrf_reading.distance_m
            azimuth, _ = pan_tilt_to_azimuth(
                position.pan_steps, position.tilt_steps, config.SENTRY_HEADING_DEG
            )
            lat, lon = compute_target_gps(
                config.SENTRY_LAT, config.SENTRY_LON, azimuth, lrf_distance
            )
            vx_px, vy_px = target.velocity_vector
            velocity_vector = {
                "vx": _convert_velocity(vx_px, lrf_distance),
                "vy": _convert_velocity(vy_px, lrf_distance),
            }

        return TelemetryRecord(
            sentry_id=config.SENTRY_ID,
            session_id=self.session_id,
            target_id=target.target_id,
            threat_score=assessment.threat_score,
            tier=assessment.tier.value,
            lat=lat,
            lon=lon,
            lrf_distance_m=lrf_distance,
            pan_angle=pan_angle,
            tilt_angle=tilt_angle,
            timestamp_utc=now,
            velocity_vector=velocity_vector,
            fsm_state=fsm_state.value if isinstance(fsm_state, FSMState) else str(fsm_state),
        )

    def emit(self, record: TelemetryRecord) -> None:
        """Serialise and emit a TelemetryRecord to disk and MQTT.

        Args:
            record: The TelemetryRecord to emit.
        """
        try:
            payload = json.dumps(dataclasses.asdict(record))
        except ValueError as exc:
            logger.error("[TELEMETRY] JSON serialization failed (nan/inf?): %s", exc)
            return
        self._jsonl_logger.info(payload)
        now = time.monotonic()
        if now - self._last_mqtt_publish >= self._mqtt_interval_s:
            self._last_mqtt_publish = now
            try:
                self._mqtt.publish_async(payload)
            except Exception as exc:
                logger.warning("[TELEMETRY] MQTT publish failed (non-fatal): %s", exc)
