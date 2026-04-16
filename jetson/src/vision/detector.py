"""YOLOv8 object detector returning a typed list of Detection objects.

Catches TensorRT / model-load failures and re-raises them with the
``[AI]`` log prefix so the caller (main.py) can handle fatal startup errors.
"""

from __future__ import annotations

import logging

import numpy as np

import config
from sentry_types import Detection

logger = logging.getLogger(__name__)


class ObjectDetector:
    """Run YOLOv8 inference and return typed Detection objects.

    Example:
        >>> detector = ObjectDetector()
        >>> detections = detector.detect(frame.data)

    Attributes:
        model: The loaded YOLO model instance.
    """

    def __init__(self) -> None:
        """Load the YOLOv8 model and perform a warm-up inference.

        Raises:
            RuntimeError: If the model cannot be loaded (TRT engine missing,
                assertion error, or file not found).  The error message is
                prefixed with ``[AI]`` for consistent log parsing.
        """
        logger.info("[AI] Loading model: %s", config.MODEL_PATH)
        try:
            from ultralytics import YOLO  # type: ignore[import]
            self.model = YOLO(config.MODEL_PATH)
        except (RuntimeError, AssertionError, FileNotFoundError) as exc:
            msg = f"[AI] Model load failed: {exc}"
            logger.critical(msg)
            raise RuntimeError(msg) from exc

        # Warm-up: run a single inference on a black dummy frame so that
        # TensorRT engine initialisation cost is paid at startup, not on
        # the first real frame.
        logger.info("[AI] Warming up model with dummy frame…")
        dummy = np.zeros((config.CAMERA_HEIGHT, config.CAMERA_WIDTH, 3), dtype=np.uint8)
        try:
            self.model.predict(
                dummy,
                conf=config.CONF_THRESHOLD,
                classes=[config.TARGET_CLASS_ID],
                verbose=False,
            )
        except Exception as exc:
            logger.warning("[AI] Warm-up failed (non-fatal): %s", exc)
        logger.info("[AI] Model ready.")

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run inference on a BGR frame and return all person detections.

        Args:
            frame: A BGR numpy array of shape ``(height, width, 3)``.

        Returns:
            A list of Detection objects for every bounding box that meets the
            confidence threshold and matches the target class ID.  Returns an
            empty list when no targets are found.
        """
        try:
            results = self.model.predict(
                frame,
                conf=config.CONF_THRESHOLD,
                classes=[config.TARGET_CLASS_ID],
                verbose=False,
            )
        except Exception:
            logger.exception("[DETECTOR] Inference failed")
            return []

        detections: list[Detection] = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                area = (x2 - x1) * (y2 - y1)
                detections.append(
                    Detection(
                        bbox=(x1, y1, x2, y2),
                        confidence=confidence,
                        class_id=class_id,
                        centroid=(cx, cy),
                        area=area,
                    )
                )
        return detections
