"""Threat scoring engine.

Converts a TrackedTarget into a ThreatAssessment using a weighted formula
whose components reflect target distance, motion speed, grouping density, and
time of day.  All weights are configurable in ``config.py``.
"""

from __future__ import annotations

import datetime
import logging
import math

import config
from sentry_types import FSMState, ThreatAssessment, ThreatTier, TrackedTarget

logger = logging.getLogger(__name__)

# Maximum bbox area used to normalise the distance score (full 480×320 frame).
_MAX_AREA: int = config.CAMERA_WIDTH * config.CAMERA_HEIGHT


class ThreatScorer:
    """Compute a normalised threat score for a single tracked target.

    Example:
        >>> scorer = ThreatScorer()
        >>> assessment = scorer.score(target, all_targets, lrf_enabled=True)
    """

    def score(
        self,
        target: TrackedTarget,
        all_targets: list[TrackedTarget],
        lrf_enabled: bool,
    ) -> ThreatAssessment:
        """Compute a ThreatAssessment for the given target.

        Args:
            target: The TrackedTarget to score.
            all_targets: All currently tracked targets (used for grouping score).
            lrf_enabled: Whether the laser rangefinder is enabled.

        Returns:
            A ThreatAssessment containing the score, tier, LRF flag, and
            recommended FSM state.
        """
        raw = (
            config.W_DISTANCE * self._distance_score(target)
            + config.W_MOTION * self._motion_score(target)
            + config.W_GROUPING * self._grouping_score(target, all_targets)
            + config.W_TIME_OF_DAY * self._time_score()
        )
        # Scale raw [0,1] to [0,100] and clamp.
        score = max(0.0, min(100.0, raw * 100.0))

        tier = self._classify(score)
        lrf_required = lrf_enabled and tier in (ThreatTier.MED, ThreatTier.HIGH)
        recommended_state = self._recommended_state(tier)

        return ThreatAssessment(
            target_id=target.target_id,
            threat_score=score,
            tier=tier,
            lrf_required=lrf_required,
            recommended_state=recommended_state,
        )

    # ------------------------------------------------------------------
    # Score components  (each returns a float in [0.0, 1.0])
    # ------------------------------------------------------------------

    def _distance_score(self, target: TrackedTarget) -> float:
        """Larger bounding box means closer target means higher threat.

        Args:
            target: The target whose bbox area is used.

        Returns:
            Normalised distance score in [0.0, 1.0].
        """
        max_area = max(_MAX_AREA, 1)
        return min(1.0, target.area / max_area)

    def _motion_score(self, target: TrackedTarget) -> float:
        """Faster-moving targets are more threatening.

        Args:
            target: The target whose velocity_vector is used.

        Returns:
            Normalised motion score in [0.0, 1.0].
        """
        vx, vy = target.velocity_vector
        speed = math.hypot(vx, vy)
        # Saturate at 200 px/frame.
        return min(1.0, speed / 200.0)

    def _grouping_score(
        self, target: TrackedTarget, all_targets: list[TrackedTarget]
    ) -> float:
        """More targets within GROUP_RADIUS_PX means higher threat.

        Args:
            target: The target whose centroid is the reference point.
            all_targets: All currently tracked targets.

        Returns:
            Normalised grouping score in [0.0, 1.0].
        """
        cx, cy = target.centroid
        nearby = sum(
            1
            for t in all_targets
            if t.target_id != target.target_id
            and math.hypot(t.centroid[0] - cx, t.centroid[1] - cy)
            <= config.GROUP_RADIUS_PX
        )
        # +1 to include self.
        count = nearby + 1
        return min(1.0, count / max(config.GROUP_MAX_COUNT, 1))

    def _time_score(self) -> float:
        """Night hours score 1.0; daytime scores 0.5.

        Returns:
            1.0 during night hours, 0.5 otherwise.
        """
        hour = datetime.datetime.utcnow().hour
        start = config.NIGHT_START_HOUR
        end = config.NIGHT_END_HOUR
        if start > end:
            # Night spans midnight, e.g. 20..6
            is_night = hour >= start or hour < end
        else:
            is_night = start <= hour < end
        return 1.0 if is_night else 0.5

    # ------------------------------------------------------------------
    # Tier + state mapping
    # ------------------------------------------------------------------

    def _classify(self, score: float) -> ThreatTier:
        if score >= config.HIGH_THREAT_THRESHOLD:
            return ThreatTier.HIGH
        if score >= config.MED_THREAT_THRESHOLD:
            return ThreatTier.MED
        return ThreatTier.LOW

    def _recommended_state(self, tier: ThreatTier) -> FSMState:
        mapping = {
            ThreatTier.LOW: FSMState.SCAN,
            ThreatTier.MED: FSMState.TRACK,
            ThreatTier.HIGH: FSMState.ACQUIRE,
        }
        return mapping[tier]
