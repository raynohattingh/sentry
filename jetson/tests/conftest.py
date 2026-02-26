"""Shared pytest fixtures for Sentry Jetson Core unit and integration tests.

sys.path is set up here so all tests can ``import`` directly from
``jetson/src/`` without package-relative gymnastics.
"""

from __future__ import annotations

import sys
import os
import threading

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Path setup — add jetson/src to sys.path so tests can do `import config` etc.
# ---------------------------------------------------------------------------
_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# The stdlib 'types' module shadows our types.py if imported as 'types'.
# Load our types.py under the alias 'sentry_types' so tests use that name.
import importlib.util as _ilu

def _load_src_module(alias: str, rel_filename: str):
    """Load a src module under an alias, registering in sys.modules first."""
    full_path = os.path.join(_SRC_DIR, rel_filename)
    spec = _ilu.spec_from_file_location(alias, full_path)
    mod = _ilu.module_from_spec(spec)
    mod.__package__ = ""
    # Register BEFORE exec so dataclass __module__ lookups work.
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod

if "sentry_types" not in sys.modules:
    _load_src_module("sentry_types", "types.py")


# ---------------------------------------------------------------------------
# MockCamera
# ---------------------------------------------------------------------------


class _MockCamera:
    """In-memory mock satisfying CameraProtocol."""

    def __init__(self) -> None:
        self.fail_read: bool = False
        self._stopped: bool = False
        self._width: int = 480
        self._height: int = 320
        self.next_frame: np.ndarray | None = None

    @property
    def is_open(self) -> bool:
        return not self._stopped

    def read(self):
        if self.fail_read or self._stopped:
            return None
        import datetime
        from sentry_types import Frame  # type: ignore[import]

        data = (
            self.next_frame
            if self.next_frame is not None
            else np.zeros((self._height, self._width, 3), dtype=np.uint8)
        )
        return Frame(
            data=data,
            timestamp_utc=datetime.datetime.utcnow().isoformat() + "Z",
            width=self._width,
            height=self._height,
        )

    def stop(self) -> None:
        self._stopped = True


@pytest.fixture
def mock_camera() -> _MockCamera:
    return _MockCamera()


# ---------------------------------------------------------------------------
# MockSerial
# ---------------------------------------------------------------------------


class _MockSerial:
    def __init__(self) -> None:
        self.written: list[bytes] = []
        self.incoming: list[str] = []
        self._connected: bool = True

    @property
    def is_connected(self) -> bool:
        return self._connected

    def write(self, data: bytes) -> None:
        self.written.append(data)

    def read_line(self) -> str | None:
        if self.incoming:
            return self.incoming.pop(0)
        return None

    def close(self) -> None:
        self._connected = False


@pytest.fixture
def mock_serial() -> _MockSerial:
    return _MockSerial()


# ---------------------------------------------------------------------------
# MockMQTTPublisher
# ---------------------------------------------------------------------------


class _MockMQTTPublisher:
    def __init__(self) -> None:
        self.published: list[str] = []
        self._lock = threading.Lock()

    def publish_async(self, payload: str) -> None:
        with self._lock:
            self.published.append(payload)


@pytest.fixture
def mock_mqtt() -> _MockMQTTPublisher:
    return _MockMQTTPublisher()


# ---------------------------------------------------------------------------
# Shared data helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def black_frame_data() -> np.ndarray:
    return np.zeros((320, 480, 3), dtype=np.uint8)
