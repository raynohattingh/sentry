"""Centroid-based multi-target tracker.

Uses ``scipy.spatial.distance.cdist`` for efficient O(n²) centroid matching
between detected bounding boxes and existing tracked targets.

Reference: PyImageSearch centroid tracking algorithm.
"""

from __future__ import annotations

import datetime
import logging
from collections import OrderedDict
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

import config
from sentry_types import Detection, TrackedTarget

logger = logging.getLogger(__name__)


class CentroidTracker:
    """Assign persistent IDs to detections across frames using centroid proximity.

    Example:
        >>> tracker = CentroidTracker(max_disappeared=30)
        >>> targets = tracker.update(detections)

    Attributes:
        max_disappeared: Number of consecutive frames without a match before a
            target is permanently deregistered.
        max_distance: Maximum centroid displacement (pixels) for a valid match.
    """

    def __init__(
        self,
        max_disappeared: int | None = None,
        max_distance: int | None = None,
    ) -> None:
        """Initialise the tracker.

        Args:
            max_disappeared: Frames without detection before deregistration.
                Defaults to ``config.MAX_DISAPPEARED``.
            max_distance: Maximum centroid jump for same-ID matching.
                Defaults to ``config.MAX_CENTROID_DISTANCE``.
        """
        self.max_disappeared: int = (
            max_disappeared if max_disappeared is not None else config.MAX_DISAPPEARED
        )
        self.max_distance: int = (
            max_distance if max_distance is not None else config.MAX_CENTROID_DISTANCE
        )

        # Monotonic ID counter — resets to 0 at class instantiation (per session).
        self._next_id: int = 0

        # OrderedDict maps target_id -> centroid (cx, cy)
        self._centroids: OrderedDict[int, tuple[int, int]] = OrderedDict()
        # OrderedDict maps target_id -> disappeared frame count
        self._disappeared: OrderedDict[int, int] = OrderedDict()
        # Previous centroid for velocity calculation
        self._prev_centroids: dict[int, tuple[int, int]] = {}
        # Latest bounding boxes and areas
        self._bboxes: dict[int, tuple[int, int, int, int]] = {}
        self._areas: dict[int, int] = {}
        self._last_seen: dict[int, str] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register(self, detection: Detection) -> int:
        """Register a new target and assign the next available ID.

        Args:
            detection: The Detection to register.

        Returns:
            The newly assigned target_id.
        """
        tid = self._next_id
        self._next_id += 1
        self._centroids[tid] = detection.centroid
        self._disappeared[tid] = 0
        self._prev_centroids[tid] = detection.centroid
        self._bboxes[tid] = detection.bbox
        self._areas[tid] = detection.area
        self._last_seen[tid] = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        return tid

    def _deregister(self, tid: int) -> None:
        """Remove all state for the given target ID.

        Args:
            tid: The target_id to deregister.
        """
        del self._centroids[tid]
        del self._disappeared[tid]
        self._prev_centroids.pop(tid, None)
        self._bboxes.pop(tid, None)
        self._areas.pop(tid, None)
        self._last_seen.pop(tid, None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, detections: list[Detection]) -> list[TrackedTarget]:
        """Update tracker state with the latest detections and return tracked targets.

        Args:
            detections: List of Detection objects from the current frame.

        Returns:
            List of TrackedTarget objects with persistent IDs and velocity vectors.
        """
        # No detections — increment disappeared for all existing targets.
        if not detections:
            for tid in list(self._disappeared.keys()):
                self._disappeared[tid] += 1
                if self._disappeared[tid] > self.max_disappeared:
                    self._deregister(tid)
            return self._build_output()

        # No existing targets — register all new detections.
        if not self._centroids:
            for det in detections:
                self._register(det)
            return self._build_output()

        # Match detections to existing targets using cdist.
        existing_ids = list(self._centroids.keys())
        existing_centroids = np.array(list(self._centroids.values()), dtype=float)
        input_centroids = np.array([d.centroid for d in detections], dtype=float)

        # Distance matrix: shape (n_existing, n_detections)
        dist_matrix = cdist(existing_centroids, input_centroids)

        # Optimal matching via the Hungarian algorithm.
        row_indices, col_indices = linear_sum_assignment(dist_matrix)

        used_rows: set[int] = set()
        used_cols: set[int] = set()

        for row, col in zip(row_indices, col_indices):
            if dist_matrix[row, col] > self.max_distance:
                continue

            tid = existing_ids[row]
            det = detections[col]
            now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

            # Save previous centroid BEFORE updating current.
            self._prev_centroids[tid] = self._centroids[tid]
            self._centroids[tid] = det.centroid
            self._disappeared[tid] = 0
            self._bboxes[tid] = det.bbox
            self._areas[tid] = det.area
            self._last_seen[tid] = now

            used_rows.add(row)
            used_cols.add(col)

        # Increment disappeared for unmatched existing targets.
        unused_rows = set(range(len(existing_ids))) - used_rows
        for row in unused_rows:
            tid = existing_ids[row]
            self._disappeared[tid] += 1
            if self._disappeared[tid] > self.max_disappeared:
                self._deregister(tid)

        # Register unmatched detections as new targets.
        unused_cols = set(range(len(detections))) - used_cols
        for col in unused_cols:
            self._register(detections[col])

        return self._build_output()

    def _build_output(self) -> list[TrackedTarget]:
        """Construct TrackedTarget list from current internal state.

        Returns:
            Ordered list of active TrackedTarget objects.
        """
        result: list[TrackedTarget] = []
        for tid in self._centroids:
            cur = self._centroids[tid]
            prev = self._prev_centroids.get(tid, cur)
            vx = float(cur[0] - prev[0])
            vy = float(cur[1] - prev[1])
            result.append(
                TrackedTarget(
                    target_id=tid,
                    centroid=cur,
                    bbox=self._bboxes.get(tid, (0, 0, 0, 0)),
                    velocity_vector=(vx, vy),
                    disappeared_frames=self._disappeared[tid],
                    area=self._areas.get(tid, 0),
                    last_seen_utc=self._last_seen.get(
                        tid, datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
                    ),
                )
            )
        return result
