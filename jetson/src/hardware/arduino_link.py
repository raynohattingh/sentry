"""Arduino serial link — velocity commands, LRF trigger, and position feedback.

Injects ``SerialProtocol`` via the constructor so the hardware can be mocked
in tests.  Includes a background read thread that parses incoming frames,
a heartbeat watchdog, and a full reconnect loop.

Serial protocol:
    Send:    ``V {pan:.2f} {tilt:.2f}\\n``  (velocity command)
             ``L\\n``                         (fire LRF)
    Receive: ``POS <pan_steps> <tilt_steps>`` (position feedback)
             ``DIST <float>``                  (LRF distance in metres;
                                                negative = error sentinel)
"""

from __future__ import annotations

import datetime
import logging
import threading
import time

import config
from comms.serial_io import SerialPort, SerialProtocol, parse_frame
from sentry_types import LRFReading, LimitEvent, TurretPosition

logger = logging.getLogger(__name__)


class ArduinoLink:
    """Manages bidirectional communication with the Arduino motor controller.

    Example:
        >>> link = ArduinoLink()
        >>> link.connect()
        >>> link.send_velocity(100.0, -50.0)
        >>> link.fire_lrf()

    Attributes:
        _serial: The injected SerialProtocol instance.
    """

    def __init__(self, serial_port: SerialProtocol | None = None) -> None:
        """Initialise the link.

        Args:
            serial_port: Optional SerialProtocol to inject (used in tests).
                When None, a real ``SerialPort`` is created.
        """
        self._serial: SerialProtocol = serial_port or SerialPort()
        self._lock: threading.RLock = threading.RLock()
        self._position: TurretPosition = TurretPosition(
            pan_steps=0,
            tilt_steps=0,
            received_utc=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        self._lrf_reading: LRFReading | None = None
        self._last_limit_event: LimitEvent | None = None
        self._validated_switches: set[str] = set()
        self._last_pos_received_ns: int = 0
        self._started_ns: int = time.monotonic_ns()
        self._read_thread: threading.Thread | None = None
        self._running: bool = False

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Open the serial connection and start the background read thread.

        Returns:
            True on success, False if the port could not be opened.
        """
        try:
            if isinstance(self._serial, SerialPort):
                self._serial.open(config.SERIAL_PORT, config.BAUD_RATE)
            time.sleep(0.5)  # brief settle time
            logger.info("[SERIAL] Connected to %s.", config.SERIAL_PORT)
            self._running = True
            self._start_read_thread()
            return True
        except Exception as exc:
            logger.error("[SERIAL] Connection failed: %s", exc)
            return False

    def _start_read_thread(self) -> None:
        """Start the background frame-reader thread if not already running."""
        if self._read_thread and self._read_thread.is_alive():
            return
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()

    def _read_loop(self) -> None:
        """Background thread: continuously read and parse serial frames."""
        while self._running:
            if not self._serial.is_connected:
                time.sleep(0.01)
                continue
            try:
                line = self._serial.read_line()
                if line is None:
                    time.sleep(0.001)
                    continue
                parsed = parse_frame(line)
                self._handle_parsed_frame(parsed)
            except Exception as exc:
                logger.warning("[SERIAL] Read error: %s", exc)
                time.sleep(0.01)

    def _handle_parsed_frame(
        self,
        parsed: LRFReading | LimitEvent | TurretPosition | None,
    ) -> None:
        if isinstance(parsed, TurretPosition):
            with self._lock:
                self._position = parsed
                self._last_pos_received_ns = time.monotonic_ns()
            return
        if isinstance(parsed, LRFReading):
            with self._lock:
                self._lrf_reading = parsed
            return
        if isinstance(parsed, LimitEvent):
            with self._lock:
                self._last_limit_event = parsed
                self._validated_switches.add(parsed.switch_key)
            logger.info("[SERIAL] Limit event observed: %s", parsed.switch_key)

    # ------------------------------------------------------------------
    # Command senders
    # ------------------------------------------------------------------

    def send_velocity(self, pan_speed: float, tilt_speed: float) -> None:
        """Send a velocity command to the Arduino.

        Args:
            pan_speed: Pan velocity in steps/sec (positive = right).
            tilt_speed: Tilt velocity in steps/sec (positive = up).
        """
        if not self._serial.is_connected:
            return
        cmd = f"V {pan_speed:.2f} {tilt_speed:.2f}\n"
        with self._lock:
            try:
                self._serial.write(cmd.encode())
            except Exception as exc:
                logger.error("[SERIAL] Write failed: %s — reconnecting…", exc)
                self._reconnect()

    def fire_lrf(self) -> None:
        """Send the LRF trigger command (``L\\n``) to the Arduino."""
        if not self._serial.is_connected:
            return
        with self._lock:
            try:
                self._serial.write(b"L\n")
            except Exception as exc:
                logger.error("[SERIAL] LRF trigger failed: %s", exc)

    # ------------------------------------------------------------------
    # Reconnect logic
    # ------------------------------------------------------------------

    def _reconnect(self) -> None:
        """Perform a best-effort reconnection sequence.

        Sends a zero-velocity command, closes the port, waits, and retries.
        Resets position to (0, 0) on success.
        """
        try:
            self._serial.write(b"V 0.00 0.00\n")
        except Exception:
            pass
        self._serial.close()
        logger.warning("[SERIAL] Disconnected — retrying in %.1fs…",
                       config.SERIAL_RETRY_INTERVAL_S)
        time.sleep(config.SERIAL_RETRY_INTERVAL_S)

        if isinstance(self._serial, SerialPort):
            try:
                self._serial.open(config.SERIAL_PORT, config.BAUD_RATE)
                with self._lock:
                    self._position = TurretPosition(
                        0, 0, datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
                    )
                logger.info("[SERIAL] Reconnected.")
            except Exception as exc:
                logger.error("[SERIAL] Reconnect failed: %s", exc)

    # ------------------------------------------------------------------
    # State properties
    # ------------------------------------------------------------------

    def is_heartbeat_alive(self) -> bool:
        """Return True if a POS frame was received within the heartbeat timeout.

        Returns:
            True when the last POS message arrived within
            ``config.SERIAL_HEARTBEAT_TIMEOUT_S``.
        """
        if self._last_pos_received_ns == 0:
            return (time.monotonic_ns() - self._started_ns) < 10_000_000_000
        elapsed_s = (time.monotonic_ns() - self._last_pos_received_ns) / 1e9
        return elapsed_s < config.SERIAL_HEARTBEAT_TIMEOUT_S

    @property
    def current_position(self) -> TurretPosition:
        """The most recently decoded turret position.

        Returns:
            TurretPosition with the latest pan/tilt step counts.
        """
        with self._lock:
            return self._position

    @property
    def last_lrf_reading(self) -> LRFReading | None:
        """The most recently decoded LRF reading, or None if no reading yet.

        Returns:
            LRFReading or None.
        """
        with self._lock:
            return self._lrf_reading

    @property
    def last_limit_event(self) -> LimitEvent | None:
        with self._lock:
            return self._last_limit_event

    @property
    def validated_switches(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._validated_switches))

    def is_switch_validated(self, switch_key: str) -> bool:
        with self._lock:
            return switch_key in self._validated_switches

    def all_required_switches_validated(self) -> bool:
        with self._lock:
            return LimitEvent.required_switch_keys().issubset(self._validated_switches)

    def reset_limit_validation(self) -> None:
        with self._lock:
            self._last_limit_event = None
            self._validated_switches.clear()

    def stop(self) -> None:
        """Stop the read thread and close the serial connection."""
        self._running = False
        try:
            self._serial.write(b"V 0.00 0.00\n")
        except Exception:
            pass
        self._serial.close()
