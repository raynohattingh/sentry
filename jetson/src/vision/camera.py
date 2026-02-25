"""Threaded video capture with GStreamer -> V4L2 fallback.

Implements CameraProtocol (read/stop) so tests can inject a mock without
touching OpenCV.  All log messages use the ``[CAMERA]`` prefix.
"""

from __future__ import annotations

import datetime
import logging
import threading
import time
from typing import Protocol, runtime_checkable

import cv2
import numpy as np

import config
from sentry_types import Frame

logger = logging.getLogger(__name__)


@runtime_checkable
class CameraProtocol(Protocol):
    """Structural interface for cameras — satisfied by ThreadedCamera and mocks.

    Any object implementing ``read()``, ``stop()``, and ``is_open`` qualifies.
    """

    @property
    def is_open(self) -> bool:
        """True while the camera is capturing frames."""
        ...

    def read(self) -> Frame | None:
        """Return the latest captured Frame, or None if unavailable."""
        ...

    def stop(self) -> None:
        """Release capture resources and stop the background thread."""
        ...


class ThreadedCamera:
    """Grab frames in a background thread for zero-latency reads.

    The capture thread runs at camera speed; the main loop reads the
    most recently captured frame without blocking.

    Example:
        >>> cam = ThreadedCamera()
        >>> cam.start()
        >>> frame = cam.read()
        >>> cam.stop()
    """

    def __init__(self) -> None:
        """Initialise capture, trying GStreamer first and V4L2 as fallback."""
        self._frame: Frame | None = None
        self._running: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._cap: cv2.VideoCapture | None = None
        self._fault_count: int = 0

        self._open_capture()

    def _open_capture(self) -> None:
        """Open the video capture device.

        Attempts GStreamer first (if ``config.USE_GSTREAMER`` is True),
        then falls back to V4L2.

        Raises:
            RuntimeError: If neither GStreamer nor V4L2 could open the device.
        """
        if config.USE_GSTREAMER:
            logger.info("[CAMERA] Attempting GStreamer pipeline…")
            try:
                cap = cv2.VideoCapture(config.GST_PIPELINE, cv2.CAP_GSTREAMER)
                if cap.isOpened():
                    self._cap = cap
                    logger.info("[CAMERA] GStreamer pipeline opened successfully.")
                    return
                cap.release()
            except Exception as exc:
                logger.warning("[CAMERA] GStreamer error: %s — falling back to V4L2.", exc)

        logger.info("[CAMERA] Opening V4L2 device index %d.", config.CAMERA_INDEX)
        cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))

        if not cap.isOpened():
            logger.error(
                "[CAMERA] CRITICAL: Could not open any video source. "
                "Check that no other process holds /dev/video%d.",
                config.CAMERA_INDEX,
            )
            raise RuntimeError("[CAMERA] Could not open any video source.")

        self._cap = cap
        logger.info("[CAMERA] V4L2 backend opened. Backend: %s", cap.getBackendName())

    @property
    def is_open(self) -> bool:
        """True while the capture thread is running."""
        return self._running

    def start(self) -> "ThreadedCamera":
        """Start the background capture thread.

        Returns:
            self — allows fluent chaining: ``cam = ThreadedCamera().start()``.
        """
        self._running = True
        t = threading.Thread(target=self._update, daemon=True)
        t.start()
        logger.info("[CAMERA] Capture thread started.")
        return self

    def _update(self) -> None:
        """Background thread: read frames continuously until stopped."""
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                time.sleep(config.SERIAL_RETRY_INTERVAL_S)
                continue

            ret, raw = self._cap.read()
            if ret and raw is not None:
                self._fault_count = 0
                now = datetime.datetime.utcnow().isoformat() + "Z"
                frame = Frame(data=raw, timestamp_utc=now,
                              width=config.CAMERA_WIDTH, height=config.CAMERA_HEIGHT)
                with self._lock:
                    self._frame = frame
            else:
                self._fault_count += 1
                if self._fault_count >= config.CAMERA_FAULT_THRESHOLD:
                    logger.warning("[CAMERA] Disconnected — retrying in %.1fs…",
                                   config.SERIAL_RETRY_INTERVAL_S)
                    if self._cap:
                        self._cap.release()
                    time.sleep(config.SERIAL_RETRY_INTERVAL_S)
                    try:
                        self._open_capture()
                        self._fault_count = 0
                        logger.info("[CAMERA] Reconnected — resuming pipeline.")
                    except RuntimeError:
                        pass
                else:
                    time.sleep(0.01)

    def read(self) -> Frame | None:
        """Return the most recently captured Frame.

        Returns:
            The latest Frame, or None if no frame has been captured yet.
        """
        with self._lock:
            if self._frame is None:
                return None
            return Frame(
                data=self._frame.data.copy(),
                timestamp_utc=self._frame.timestamp_utc,
                width=self._frame.width,
                height=self._frame.height,
            )

    def stop(self) -> None:
        """Stop the capture thread and release the camera device."""
        self._running = False
        if self._cap:
            self._cap.release()
        logger.info("[CAMERA] Stopped.")


# Backwards-compat alias used by existing code.
CameraStream = ThreadedCamera
