"""Low-level serial port abstraction.

Provides ``SerialProtocol`` (typing.Protocol) for mock injection in tests,
``SerialPort`` as the concrete hardware implementation, and ``parse_frame``
for turning raw serial lines into typed objects.

Background read thread, heartbeat tracking, and reconnect logic live in
``hardware/arduino_link.py``; this module only handles open/read/write/close.
"""

from __future__ import annotations

import datetime
import logging
import re
from typing import Protocol, runtime_checkable

import config
from sentry_types import LRFReading, TurretPosition

logger = logging.getLogger(__name__)

# Pre-compiled regex for valid serial frames.
_FRAME_RE = re.compile(r"^(DIST \d+(\.\d+)?|POS -?\d+ -?\d+)$")


# ---------------------------------------------------------------------------
# Frame parser (module-level utility used by ArduinoLink)
# ---------------------------------------------------------------------------


def parse_frame(line: str) -> LRFReading | TurretPosition | None:
    """Parse a raw serial line into a typed object.

    Args:
        line: A stripped string from the serial port, e.g. ``"DIST 150.50"``
            or ``"POS 1000 -250"``.

    Returns:
        A ``LRFReading``, ``TurretPosition``, or ``None`` for empty lines.
        Returns an invalid ``LRFReading`` if the frame looks like a DIST
        command but is malformed.
    """
    line = line.strip()
    now = datetime.datetime.utcnow().isoformat() + "Z"

    if not line:
        return None

    if _FRAME_RE.match(line):
        if line.startswith("DIST"):
            _, val = line.split()
            return LRFReading(distance_m=float(val), valid=True, received_utc=now)
        if line.startswith("POS"):
            _, pan, tilt = line.split()
            return TurretPosition(pan_steps=int(pan), tilt_steps=int(tilt), received_utc=now)

    # Frame does not match any known pattern.
    if line.startswith("DIST"):
        # Looks like a DIST command but is malformed.
        logger.warning("[SERIAL] Malformed frame discarded: %s", line)
        return LRFReading(distance_m=None, valid=False, received_utc=now)

    logger.warning("[SERIAL] Malformed frame discarded: %s", line)
    return None


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SerialProtocol(Protocol):
    """Structural interface for serial ports.

    Implemented by ``SerialPort`` (hardware) and ``_MockSerial`` (tests).
    """

    @property
    def is_connected(self) -> bool:
        """True while the serial port is open."""
        ...

    def write(self, data: bytes) -> None:
        """Write raw bytes to the port.

        Args:
            data: Bytes to transmit.
        """
        ...

    def read_line(self) -> str | None:
        """Read one line from the port.

        Returns:
            A decoded string without the trailing newline, or None when the
            read buffer is empty or the port is not connected.
        """
        ...

    def close(self) -> None:
        """Close the serial connection."""
        ...


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------


class SerialPort:
    """Wraps ``pyserial.Serial`` to satisfy ``SerialProtocol``.

    Example:
        >>> port = SerialPort()
        >>> port.open("/dev/ttyUSB0", 115200)
        >>> port.write(b"V 0.00 0.00\\n")
        >>> line = port.read_line()
        >>> port.close()
    """

    def __init__(self) -> None:
        """Create an unopened serial port."""
        self._serial = None  # type: ignore[assignment]
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        """True while the underlying serial device is open."""
        return self._connected and self._serial is not None

    def open(self, port: str, baud: int) -> None:
        """Open the serial connection.

        Args:
            port: Device path, e.g. ``/dev/ttyUSB0``.
            baud: Baud rate, e.g. ``115200``.

        Raises:
            serial.SerialException: If the port cannot be opened.
        """
        import serial

        self._serial = serial.Serial(port, baud, timeout=0.05)
        self._connected = True
        logger.info("[SERIAL] Opened %s @ %d baud.", port, baud)

    def write(self, data: bytes) -> None:
        """Write raw bytes to the serial port.

        Args:
            data: Bytes to transmit.
        """
        if self._serial:
            self._serial.write(data)

    def read_line(self) -> str | None:
        """Read one line from the serial port.

        Returns:
            A stripped string, or None if the buffer was empty.
        """
        if not self._serial:
            return None
        raw = self._serial.readline()
        if not raw:
            return None
        return raw.decode("ascii", errors="replace").strip()

    def close(self) -> None:
        """Close the serial connection."""
        if self._serial:
            self._serial.close()
        self._connected = False
        logger.info("[SERIAL] Port closed.")
