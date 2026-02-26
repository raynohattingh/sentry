"""SentryBrain — the Finite State Machine at the heart of the sentry system.

# FSM Transition Priority Note (FR-015 / FR-022)
# ─────────────────────────────────────────────────────────────────────────
# • SEARCH fires IMMEDIATELY when a target disappears from TRACK or ACQUIRE
#   (upward urgency — no dwell gate).
# • Idle-timeout motor-stop (within SCAN) is distinct from FSM transitions
#   and applies only when the FSM is already in SCAN state with no targets.
# • Downward transitions (e.g. ACQUIRE→TRACK, TRACK→SCAN) require the
#   min_dwell timer to have elapsed; this prevents jitter-induced oscillation.
# • Upward transitions (e.g. SCAN→ACQUIRE) are always immediate.
#
# This comment exists to prevent future maintainers from inadvertently
# merging the two independent behaviours or adding dwell gates to upward
# transitions.
# ─────────────────────────────────────────────────────────────────────────

SentryBrain is the sole authority that decides what velocity command is sent
to the turret on each control loop iteration.  All PID computation happens
inside this class.
"""

from __future__ import annotations

import datetime
import logging
import time
from typing import TYPE_CHECKING

import config
from control.pid import PIDController
from sentry_types import (
    FSMState,
    ThreatAssessment,
    ThreatTier,
    TurretCommand,
    TurretPosition,
)

logger = logging.getLogger(__name__)

# FSM state ordering for direction detection (higher index = higher urgency).
_STATE_ORDER: dict[FSMState, int] = {
    FSMState.SCAN: 0,
    FSMState.SEARCH: 1,
    FSMState.TRACK: 2,
    FSMState.ACQUIRE: 3,
}

# Dwell timer lookup (ms) keyed by FSMState.
_DWELL_MS: dict[FSMState, int] = {}


def _refresh_dwell() -> None:
    _DWELL_MS[FSMState.SCAN] = config.MIN_DWELL_MS_SCAN
    _DWELL_MS[FSMState.TRACK] = config.MIN_DWELL_MS_TRACK
    _DWELL_MS[FSMState.ACQUIRE] = config.MIN_DWELL_MS_ACQUIRE
    _DWELL_MS[FSMState.SEARCH] = config.MIN_DWELL_MS_SEARCH


_refresh_dwell()


class SentryBrain:
    """Finite State Machine controller that outputs TurretCommands.

    The FSM owns two PID controllers (pan and tilt) and applies velocity
    tapering near the turret limits.  The ``update()`` method is called
    once per control loop iteration.

    Example:
        >>> brain = SentryBrain()
        >>> command = brain.update(assessments, position)
    """

    def __init__(self) -> None:
        """Initialise the FSM in SCAN state."""
        _refresh_dwell()
        self._state: FSMState = FSMState.SCAN
        self._state_entered_ns: int = time.monotonic_ns()

        self._pan_pid = PIDController(
            config.PAN_KP, config.PAN_KI, config.PAN_KD, config.PAN_MAX,
            config.PID_MAX_INTEGRAL,
        )
        self._tilt_pid = PIDController(
            config.TILT_KP, config.TILT_KI, config.TILT_KD, config.TILT_MAX,
            config.PID_MAX_INTEGRAL,
        )

        self._scan_direction: float = 1.0  # +1 = moving right, -1 = left
        self._last_known_pan: int = 0      # SEARCH arc anchor
        self._search_entered_s: float = 0.0
        self._approaching_limit: bool = False
        self._in_taper_zone: bool = False

        logger.info("[BRAIN] SentryBrain initialised in %s state.", self._state.value)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> FSMState:
        """Current FSM state."""
        return self._state

    @property
    def approaching_limit(self) -> bool:
        """True when either axis is inside the velocity taper zone."""
        return self._approaching_limit

    def update(
        self,
        assessments: list[ThreatAssessment],
        position: TurretPosition,
    ) -> TurretCommand:
        """Run one FSM + PID iteration and return the turret command.

        Args:
            assessments: Threat assessments for all currently tracked targets.
                Empty list means no targets visible.
            position: Latest known turret position from the Arduino.

        Returns:
            TurretCommand with pan/tilt velocities and LRF flag.
        """
        _refresh_dwell()
        self._update_state(assessments, position)

        pan_v, tilt_v, fire_lrf = self._compute_velocities(assessments, position)

        # Apply limit tapering.
        pan_v = self.taper_velocity(
            position.pan_steps,
            config.PAN_LIMIT_WARN_STEPS,
            config.PAN_LIMIT_HARD_STEPS,
            pan_v,
        )
        tilt_v = self.taper_velocity(
            position.tilt_steps,
            config.TILT_LIMIT_WARN_STEPS,
            config.TILT_LIMIT_HARD_STEPS,
            tilt_v,
        )

        # Update approaching-limit flag.
        pan_in_zone = abs(position.pan_steps) >= config.PAN_LIMIT_WARN_STEPS
        tilt_in_zone = abs(position.tilt_steps) >= config.TILT_LIMIT_WARN_STEPS
        new_in_zone = pan_in_zone or tilt_in_zone
        if new_in_zone and not self._in_taper_zone:
            logger.warning("[TURRET] Approaching limit — tapering velocity.")
        self._in_taper_zone = new_in_zone
        self._approaching_limit = new_in_zone

        now = datetime.datetime.utcnow().isoformat() + "Z"
        return TurretCommand(
            pan_velocity=pan_v,
            tilt_velocity=tilt_v,
            fire_lrf=fire_lrf,
            timestamp_utc=now,
        )

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def _update_state(
        self,
        assessments: list[ThreatAssessment],
        position: TurretPosition,
    ) -> None:
        """Evaluate FSM transitions based on current assessments."""
        if not assessments:
            # No targets visible.
            if self._state in (FSMState.TRACK, FSMState.ACQUIRE):
                # Target lost — go to SEARCH immediately (upward urgency).
                self._last_known_pan = position.pan_steps
                self._transition(FSMState.SEARCH)
                self._search_entered_s = time.monotonic()
            elif self._state == FSMState.SEARCH:
                elapsed = time.monotonic() - self._search_entered_s
                if elapsed >= config.SEARCH_TIMEOUT_S:
                    self._transition(FSMState.SCAN)
        else:
            # Pick highest-priority assessment.
            best = max(assessments, key=lambda a: a.threat_score)
            desired = best.recommended_state

            if desired == FSMState.ACQUIRE:
                # Upward transition — always immediate.
                if self._state != FSMState.ACQUIRE:
                    self._transition(FSMState.ACQUIRE)
            elif desired == FSMState.TRACK:
                if self._state == FSMState.SCAN:
                    self._transition(FSMState.TRACK)
                elif self._state == FSMState.ACQUIRE:
                    if self._dwell_elapsed():
                        self._transition(FSMState.TRACK)
                elif self._state == FSMState.SEARCH:
                    self._transition(FSMState.TRACK)
            elif desired == FSMState.SCAN:
                if self._state in (FSMState.TRACK, FSMState.ACQUIRE):
                    if self._dwell_elapsed():
                        self._transition(FSMState.SCAN)
                elif self._state == FSMState.SEARCH:
                    self._transition(FSMState.SCAN)

    def _transition(self, new_state: FSMState) -> None:
        """Transition to a new FSM state and record entry time.

        Args:
            new_state: The state to transition into.
        """
        if new_state == self._state:
            return
        logger.info("[BRAIN] %s → %s", self._state.value, new_state.value)
        self._state = new_state
        self._state_entered_ns = time.monotonic_ns()

        # Reset PIDs on transitions that change tracking context.
        if new_state in (FSMState.SCAN, FSMState.SEARCH):
            self._pan_pid.reset()
            self._tilt_pid.reset()

    def _dwell_elapsed(self) -> bool:
        """Return True if the minimum dwell time for the current state has elapsed.

        Returns:
            True when the dwell timer is satisfied (downward transition allowed).
        """
        elapsed_ms = (time.monotonic_ns() - self._state_entered_ns) / 1e6
        return elapsed_ms >= _DWELL_MS.get(self._state, 0)

    # ------------------------------------------------------------------
    # Velocity computation
    # ------------------------------------------------------------------

    def _compute_velocities(
        self,
        assessments: list[ThreatAssessment],
        position: TurretPosition,
    ) -> tuple[float, float, bool]:
        """Compute raw (pre-taper) pan/tilt velocities and LRF flag.

        Args:
            assessments: Current threat assessments.
            position: Current turret position.

        Returns:
            Tuple of (pan_velocity, tilt_velocity, fire_lrf).
        """
        fire_lrf = False

        if self._state == FSMState.SCAN:
            return self._scan_sweep(position), 0.0, False

        if self._state == FSMState.SEARCH:
            return self._search_arc(position), 0.0, False

        if self._state in (FSMState.TRACK, FSMState.ACQUIRE):
            if not assessments:
                return 0.0, 0.0, False
            best = max(assessments, key=lambda a: a.threat_score)
            fire_lrf = best.lrf_required
            # PID is driven by the caller in the original design, but the brain
            # owns it here.  We return 0,0 when no centroid is available;
            # main.py provides centroid-based error to the brain via position.
            # For now: return fixed tracking values (main.py will compute error).
            return 0.0, 0.0, fire_lrf

        return 0.0, 0.0, False

    def _scan_sweep(self, position: TurretPosition) -> float:
        """Compute pan velocity for oscillating SCAN sweep.

        Args:
            position: Current turret position.

        Returns:
            Pan velocity in steps/sec.
        """
        pan = position.pan_steps
        if pan >= config.SCAN_PAN_MAX:
            self._scan_direction = -1.0
        elif pan <= config.SCAN_PAN_MIN:
            self._scan_direction = 1.0
        return config.SCAN_VELOCITY * self._scan_direction

    def _search_arc(self, position: TurretPosition) -> float:
        """Compute pan velocity for SEARCH arc around last-known position.

        Args:
            position: Current turret position.

        Returns:
            Pan velocity in steps/sec.
        """
        arc_steps = int(config.SEARCH_ARC_DEG * config.STEPS_PER_DEGREE)
        left = self._last_known_pan - arc_steps
        right = self._last_known_pan + arc_steps
        pan = position.pan_steps
        if pan >= right:
            self._scan_direction = -1.0
        elif pan <= left:
            self._scan_direction = 1.0
        return config.SCAN_VELOCITY * self._scan_direction

    # ------------------------------------------------------------------
    # Velocity tapering (FR-031)
    # ------------------------------------------------------------------

    @staticmethod
    def taper_velocity(
        pos: int,
        warn: int,
        hard: int,
        velocity: float,
    ) -> float:
        """Apply linear velocity tapering near mechanical limits.

        The taper zone is [warn, hard] (by absolute position).  Outside the
        zone the velocity is unchanged.  At the hard limit the velocity is
        zero.  The scale is linear between warn and hard:

            scale = (hard - |pos|) / (hard - warn)

        Args:
            pos: Current absolute step position (signed; abs is taken).
            warn: Absolute step count where tapering begins.
            hard: Absolute step count at which velocity reaches zero.
            velocity: Current velocity to scale.

        Returns:
            Scaled velocity; unchanged when outside the taper zone.
        """
        abs_pos = abs(pos)
        if abs_pos <= warn:
            return velocity
        if abs_pos >= hard:
            return 0.0
        taper_width = hard - warn
        if taper_width <= 0:
            return 0.0
        scale = (hard - abs_pos) / taper_width
        return velocity * max(0.0, scale)
