"""Shared dataclasses and enums for the Sentry Jetson Core.

All data that flows between subsystems is typed here. No business logic lives
in this module — it is a pure data-model layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ThreatTier(str, Enum):
    """Threat severity classification used by ThreatScorer and SentryBrain.

    Values:
        LOW: Threat score below MED_THREAT_THRESHOLD — SCAN state, no LRF.
        MED: Threat score >= MED_THREAT_THRESHOLD — TRACK state, sampled LRF.
        HIGH: Threat score >= HIGH_THREAT_THRESHOLD — ACQUIRE state, continuous LRF.
    """

    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class FSMState(str, Enum):
    """Finite State Machine states for SentryBrain.

    Values:
        SCAN: No active target; oscillating pan sweep.
        TRACK: Active target at MED threat; sampled LRF.
        ACQUIRE: Active target at HIGH threat; continuous LRF, hard lock.
        SEARCH: Target lost; arc sweep around last-known position.
        MANUAL_OVERRIDE: Operator has taken direct control via command topic.
    """

    SCAN = "SCAN"
    TRACK = "TRACK"
    ACQUIRE = "ACQUIRE"
    SEARCH = "SEARCH"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class HousingProfile(str, Enum):
    """Physical enclosure profile that determines motion safety behavior."""

    TEST_BENCH = "TEST_BENCH"
    MVP = "MVP"

    @classmethod
    def from_raw(cls, value: str | None) -> "HousingProfile":
        if value is None:
            return cls.MVP
        try:
            return cls(value.upper())
        except ValueError:
            import logging
            logging.getLogger(__name__).warning(
                "Unknown housing profile '%s', defaulting to MVP.", value,
            )
            return cls.MVP


class LimitAxis(str, Enum):
    PAN = "PAN"
    TILT = "TILT"


class LimitDirection(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"


class LimitValidationState(str, Enum):
    BYPASSED = "BYPASSED"
    BLOCKED_INVALID_BOUNDS = "BLOCKED_INVALID_BOUNDS"
    PENDING_SWITCH_VALIDATION = "PENDING_SWITCH_VALIDATION"
    READY_HARDWARE_VALIDATED = "READY_HARDWARE_VALIDATED"


class ProtectionMode(str, Enum):
    SOFT_LIMIT_BYPASS = "SOFT_LIMIT_BYPASS"
    HARDWARE_VALIDATION_PENDING = "HARDWARE_VALIDATION_PENDING"
    HARDWARE_LIMITS_ACTIVE = "HARDWARE_LIMITS_ACTIVE"


# ---------------------------------------------------------------------------
# Vision entities
# ---------------------------------------------------------------------------


@dataclass
class Frame:
    """A single captured video frame from the camera subsystem.

    Attributes:
        data: BGR image array with shape (height, width, 3).
        timestamp_utc: ISO 8601 UTC timestamp at the moment of capture.
        width: Frame width in pixels.
        height: Frame height in pixels.
    """

    data: np.ndarray
    timestamp_utc: str
    width: int = 480
    height: int = 320

    def __post_init__(self) -> None:
        if self.data is not None and len(self.data.shape) >= 2:
            object.__setattr__(self, "height", self.data.shape[0])
            object.__setattr__(self, "width", self.data.shape[1])


@dataclass
class Detection:
    """A single YOLO detection for the target class (default: person).

    Attributes:
        bbox: Bounding box coordinates as (x1, y1, x2, y2) in pixels.
        confidence: Detection confidence in the range [0.0, 1.0].
        class_id: YOLO class identifier (0 = person for COCO).
        centroid: Centre pixel (cx, cy) derived from bbox.
        area: Bounding-box area in pixels²; used as a distance proxy.
    """

    bbox: tuple[int, int, int, int]
    confidence: float
    class_id: int
    centroid: tuple[int, int]
    area: int


@dataclass
class TrackedTarget:
    """A detection enriched with a persistent ID and motion state by CentroidTracker.

    Attributes:
        target_id: Monotonically increasing integer; resets to 0 on container restart.
        centroid: Latest (cx, cy) centroid in pixels.
        bbox: Latest bounding box (x1, y1, x2, y2) in pixels.
        velocity_vector: (vx, vy) pixels/frame; (0.0, 0.0) on first detection.
        disappeared_frames: Number of frames since the last matching detection.
        area: Latest bounding-box area (px²); used as distance proxy.
        last_seen_utc: ISO 8601 UTC timestamp of the last matched frame.
    """

    target_id: int
    centroid: tuple[int, int]
    bbox: tuple[int, int, int, int]
    velocity_vector: tuple[float, float]
    disappeared_frames: int
    area: int
    last_seen_utc: str


# ---------------------------------------------------------------------------
# Control entities
# ---------------------------------------------------------------------------


@dataclass
class ThreatAssessment:
    """Threat evaluation for a single tracked target.

    Attributes:
        target_id: Matches TrackedTarget.target_id.
        threat_score: Normalised score in [0.0, 100.0].
        tier: ThreatTier classification (LOW/MED/HIGH).
        lrf_required: True when tier is MED or HIGH and LRF is enabled.
        recommended_state: The FSMState that this threat level recommends.
    """

    target_id: int
    threat_score: float
    tier: ThreatTier
    lrf_required: bool
    recommended_state: FSMState


@dataclass
class TurretCommand:
    """Velocity command produced by SentryBrain and consumed by ArduinoLink.

    Attributes:
        pan_velocity: Pan speed in steps/sec; positive = right, negative = left.
        tilt_velocity: Tilt speed in steps/sec; positive = up, negative = down.
        fire_lrf: When True, triggers an ``L\\n`` command on the same loop tick.
        timestamp_utc: ISO 8601 UTC at command creation; used for telemetry.
    """

    pan_velocity: float
    tilt_velocity: float
    fire_lrf: bool
    timestamp_utc: str


# ---------------------------------------------------------------------------
# Hardware / I/O entities
# ---------------------------------------------------------------------------


@dataclass
class TurretPosition:
    """Turret position decoded from incoming ``POS <pan> <tilt>`` serial messages.

    Attributes:
        pan_steps: Cumulative signed step count on the pan axis; positive = right.
        tilt_steps: Cumulative signed step count on the tilt axis; positive = up.
        received_utc: ISO 8601 UTC timestamp of the last POS message.
    """

    pan_steps: int
    tilt_steps: int
    received_utc: str


@dataclass
class LRFReading:
    """Laser rangefinder measurement decoded from a ``DIST <float>`` serial message.

    Attributes:
        distance_m: Measured distance in metres; None if invalid or LRF disabled.
        valid: False when the message was malformed or LRF is disabled.
        received_utc: ISO 8601 UTC timestamp of message receipt.
    """

    distance_m: float | None
    valid: bool
    received_utc: str


@dataclass(frozen=True)
class SoftMotionBounds:
    """Inclusive software travel envelope used for test-bench operation."""

    pan_min_steps: int | None
    pan_max_steps: int | None
    tilt_min_steps: int | None
    tilt_max_steps: int | None

    @property
    def is_valid(self) -> bool:
        values = (
            self.pan_min_steps,
            self.pan_max_steps,
            self.tilt_min_steps,
            self.tilt_max_steps,
        )
        if any(value is None for value in values):
            return False
        assert self.pan_min_steps is not None
        assert self.pan_max_steps is not None
        assert self.tilt_min_steps is not None
        assert self.tilt_max_steps is not None
        return (
            self.pan_min_steps < self.pan_max_steps
            and self.tilt_min_steps < self.tilt_max_steps
        )


@dataclass(frozen=True)
class LimitEvent:
    """One observed LIMIT serial event from the Arduino controller."""

    axis: LimitAxis
    direction: LimitDirection
    received_utc: str

    @property
    def switch_key(self) -> str:
        return f"{self.axis.value}_{self.direction.value}"

    @classmethod
    def required_switch_keys(cls) -> set[str]:
        return {
            "PAN_LEFT",
            "PAN_RIGHT",
            "TILT_DOWN",
            "TILT_UP",
        }


@dataclass(frozen=True)
class SafetyStatus:
    """Authoritative motion-safety status published to operator clients."""

    sentry_id: str
    housing_profile: HousingProfile
    protection_mode: ProtectionMode
    motion_allowed: bool
    motion_block_reason: str | None
    validated_switches: tuple[str, ...] = ()
    timestamp_utc: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "sentry_id": self.sentry_id,
            "housing_profile": self.housing_profile.value,
            "protection_mode": self.protection_mode.value,
            "motion_allowed": self.motion_allowed,
            "motion_block_reason": self.motion_block_reason,
            "validated_switches": self.validated_switches,
            "timestamp_utc": self.timestamp_utc,
        }


# ---------------------------------------------------------------------------
# Telemetry entity
# ---------------------------------------------------------------------------


@dataclass
class TelemetryRecord:
    """A single telemetry snapshot serialised to JSON-lines and MQTT.

    Attributes:
        sentry_id: Identity key for the emitting sentry; used by clients to
            filter multi-sentry traffic on a shared broker.
        session_id: UUID4 generated once at process startup; immutable.
        target_id: From TrackedTarget.
        threat_score: From ThreatAssessment.
        tier: String representation of ThreatTier ("LOW" | "MED" | "HIGH").
        lat: WGS-84 latitude in decimal degrees; None when LRF is disabled or invalid.
        lon: WGS-84 longitude in decimal degrees; None when LRF is disabled or invalid.
        lrf_distance_m: Measured distance; None when LRF is disabled or reading invalid.
        pan_angle: Current pan angle in degrees (derived from pan_steps / STEPS_PER_DEGREE).
        tilt_angle: Current tilt angle in degrees (derived from tilt_steps / STEPS_PER_DEGREE).
        timestamp_utc: ISO 8601 UTC at record creation.
    """

    sentry_id: str
    session_id: str
    target_id: int
    threat_score: float
    tier: ThreatTier
    lat: float | None
    lon: float | None
    lrf_distance_m: float | None
    pan_angle: float
    tilt_angle: float
    timestamp_utc: str
    velocity_vector: dict[str, float] | None
    fsm_state: FSMState
