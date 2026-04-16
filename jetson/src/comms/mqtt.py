"""Non-blocking MQTT publisher and manual-override command subscriber.

The publisher uses a daemon thread + queue.Queue so that ``publish_async()``
never blocks the main control loop.  If the broker is unavailable the queue
fills up and overflow is silently dropped with a ``[MQTT] Queue full`` log.

The CommandSubscriber listens on ``config.MQTT_COMMAND_TOPIC``, validates
ManualCommand payloads, rate-limits them, and dispatches to TurretManager.

MQTT failures never propagate to the caller.
"""

from __future__ import annotations

import json
import logging
import math
import queue
import ssl
import threading
import time
from typing import Callable, Protocol, runtime_checkable

import config

logger = logging.getLogger(__name__)


@runtime_checkable
class MQTTProtocol(Protocol):
    """Structural interface for MQTT publishers."""

    def publish_async(self, payload: str) -> None:
        """Queue a payload for asynchronous delivery.

        Args:
            payload: JSON string to publish.
        """
        ...


class MQTTPublisher:
    """Non-blocking MQTT publisher backed by a daemon thread.

    Example:
        >>> pub = MQTTPublisher()
        >>> pub.publish_async('{"key": "value"}')

    Attributes:
        broker: MQTT broker hostname.
        port: MQTT broker port.
        topic: MQTT topic to publish to.
    """

    _BACKOFF_MAX_S: float = 30.0
    _QUEUE_MAX: int = 500

    def __init__(
        self,
        broker: str | None = None,
        port: int | None = None,
        topic: str | None = None,
    ) -> None:
        """Initialise the publisher and start the background thread.

        Args:
            broker: MQTT broker hostname. Defaults to ``config.MQTT_BROKER``.
            port: MQTT broker port. Defaults to ``config.MQTT_PORT``.
            topic: MQTT publish topic. Defaults to ``config.MQTT_TOPIC``.
        """
        self.broker: str = broker or config.MQTT_BROKER
        self.port: int = port or config.MQTT_PORT
        self.topic: str = topic or config.MQTT_TOPIC

        self._queue: queue.Queue[str] = queue.Queue(maxsize=self._QUEUE_MAX)
        self._client = None
        self._connected: bool = False

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("[MQTT] Publisher started; broker=%s:%d topic=%s",
                    self.broker, self.port, self.topic)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish_async(self, payload: str) -> None:
        """Enqueue a payload for non-blocking MQTT delivery.

        Args:
            payload: JSON string to publish to the configured topic.
        """
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            logger.warning("[MQTT] Queue full — dropping telemetry payload.")

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Background thread: connect, reconnect, and drain the queue."""
        backoff = 1.0
        while True:
            try:
                self._connect()
                backoff = 1.0  # reset on successful connect
                self._drain()
            except Exception as exc:
                logger.warning("[MQTT] Connection error: %s — retry in %.0fs.", exc, backoff)
                self._connected = False
                time.sleep(backoff)
                backoff = min(backoff * 2, self._BACKOFF_MAX_S)

    def _connect(self) -> None:
        """Establish a TLS connection to the MQTT broker."""
        try:
            import paho.mqtt.client as mqtt  # type: ignore[import]
        except ImportError:
            logger.error("[MQTT] paho-mqtt not installed — MQTT disabled.")
            time.sleep(60)
            return

        # Clean up previous client if reconnecting.
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        if config.MQTT_USERNAME:
            client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
        if config.MQTT_TLS_VERIFY:
            client.tls_set(ca_certs=config.MQTT_CA_CERT,
                           cert_reqs=ssl.CERT_REQUIRED,
                           tls_version=ssl.PROTOCOL_TLS_CLIENT)
        else:
            logger.warning("[MQTT] TLS verification DISABLED — vulnerable to MITM.")
            client.tls_set(ca_certs=None, cert_reqs=ssl.CERT_NONE,
                           tls_version=ssl.PROTOCOL_TLS_CLIENT)
            client.tls_insecure_set(True)
        client.connect(self.broker, self.port, keepalive=60)
        client.loop_start()
        self._client = client
        # Wait briefly for connection callback.
        time.sleep(1.0)

    def _drain(self) -> None:
        """Drain the queue and publish messages to the broker."""
        while True:
            try:
                payload = self._queue.get(timeout=1.0)
                if self._connected and self._client:
                    self._client.publish(self.topic, payload)
                else:
                    # Not connected — wait before retrying (avoid busy-loop).
                    time.sleep(5.0)
                    # Re-queue for next attempt.
                    try:
                        self._queue.put_nowait(payload)
                    except queue.Full:
                        pass
            except queue.Empty:
                continue
            except Exception as exc:
                logger.warning("[MQTT] Publish failed: %s", exc)
                raise  # propagate to _run to trigger reconnect

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            self._connected = True
            logger.info("[MQTT] Connected to broker %s:%d.", self.broker, self.port)
        else:
            logger.warning("[MQTT] Connect returned rc=%d.", rc)

    def _on_disconnect(self, client, userdata, rc) -> None:
        self._connected = False
        if rc != 0:
            logger.warning("[MQTT] Unexpected disconnect (rc=%d).", rc)


# ---------------------------------------------------------------------------
# CommandSubscriber — manual override inbound command handler (FR-022a)
# ---------------------------------------------------------------------------

class CommandSubscriber:
    """Subscribe to the sentry/command MQTT topic and execute ManualCommand payloads.

    Validates each message against ``config.SENTRY_ID``, rate-limits to
    ``config.COMMAND_RATE_LIMIT_HZ``, and drives the turret via a
    ``set_velocity`` callable.  A safety watchdog stops the turret if no
    command is received within ``config.COMMAND_SAFETY_TIMEOUT_S``.

    Example:
        >>> sub = CommandSubscriber(
        ...     set_velocity=turret_manager.set_velocity,
        ...     enter_override=brain.enter_override,
        ...     exit_override=brain.exit_override,
        ... )
        >>> sub.start()
    """

    def __init__(
        self,
        set_velocity: Callable[[float, float], None],
        enter_override: Callable[[], None],
        exit_override: Callable[[], None],
        broker: str | None = None,
        port: int | None = None,
    ) -> None:
        """Initialise the subscriber.

        Args:
            set_velocity: Callable accepting (pan_velocity, tilt_velocity).
            enter_override: Callable that activates manual override in SentryBrain.
            exit_override: Callable that deactivates manual override in SentryBrain.
            broker: MQTT broker hostname; defaults to config.MQTT_BROKER.
            port: MQTT broker port; defaults to config.MQTT_PORT.
        """
        self._set_velocity = set_velocity
        self._enter_override = enter_override
        self._exit_override = exit_override
        self.broker: str = broker or config.MQTT_BROKER
        self.port: int = port or config.MQTT_PORT
        self._client = None

        self._min_interval_s: float = 1.0 / config.COMMAND_RATE_LIMIT_HZ
        self._last_command_time: float = 0.0
        self._last_command_lock = threading.Lock()

        self._watchdog_thread = threading.Thread(target=self._watchdog, daemon=True)
        self._running = False

    def start(self) -> None:
        """Connect to the broker and start the subscriber loop."""
        try:
            import paho.mqtt.client as mqtt  # type: ignore[import]
        except ImportError:
            logger.error("[CMD] paho-mqtt not installed — CommandSubscriber disabled.")
            return

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        if config.MQTT_USERNAME:
            client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
        if config.MQTT_TLS_VERIFY:
            client.tls_set(ca_certs=config.MQTT_CA_CERT,
                           cert_reqs=ssl.CERT_REQUIRED,
                           tls_version=ssl.PROTOCOL_TLS_CLIENT)
        else:
            logger.warning("[CMD] TLS verification DISABLED — vulnerable to MITM.")
            client.tls_set(ca_certs=None, cert_reqs=ssl.CERT_NONE,
                           tls_version=ssl.PROTOCOL_TLS_CLIENT)
            client.tls_insecure_set(True)
        client.connect(self.broker, self.port, keepalive=60)
        self._client = client
        self._running = True
        self._watchdog_thread.start()
        client.loop_start()
        logger.info("[CMD] CommandSubscriber started; topic=%s", config.MQTT_COMMAND_TOPIC)

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            client.subscribe(config.MQTT_COMMAND_TOPIC)
            logger.info("[CMD] Subscribed to %s.", config.MQTT_COMMAND_TOPIC)
        else:
            logger.warning("[CMD] Connect returned rc=%d.", rc)

    def _on_message(self, client, userdata, msg) -> None:
        """Handle inbound ManualCommand messages."""
        now = time.monotonic()

        # Rate limiting — discard if arrived too soon.
        with self._last_command_lock:
            if now - self._last_command_time < self._min_interval_s:
                return
            self._last_command_time = now

        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("[CMD] Invalid JSON: %s", exc)
            return

        # Validate sentry_id.
        if payload.get("sentry_id") != config.SENTRY_ID:
            logger.debug("[CMD] Ignoring command for sentry_id=%s.", payload.get("sentry_id"))
            return

        pan_v = payload.get("pan_velocity", 0.0)
        tilt_v = payload.get("tilt_velocity", 0.0)

        if not isinstance(pan_v, (int, float)) or not isinstance(tilt_v, (int, float)):
            logger.warning("[CMD] Non-numeric velocities — dropping command.")
            return

        pan_v = float(pan_v)
        tilt_v = float(tilt_v)

        if not (math.isfinite(pan_v) and math.isfinite(tilt_v)):
            logger.warning("[CMD] Non-finite velocity rejected (nan/inf).")
            return

        pan_v = max(-config.PAN_MAX, min(config.PAN_MAX, pan_v))
        tilt_v = max(-config.TILT_MAX, min(config.TILT_MAX, tilt_v))

        self._enter_override()
        self._set_velocity(pan_v, tilt_v)

    def _watchdog(self) -> None:
        """Stop the turret if no command arrives within the safety timeout."""
        while self._running:
            time.sleep(0.5)
            with self._last_command_lock:
                idle_s = time.monotonic() - self._last_command_time
            if self._last_command_time > 0 and idle_s > config.COMMAND_SAFETY_TIMEOUT_S:
                logger.info("[CMD] Safety timeout — stopping turret and exiting override.")
                self._set_velocity(0.0, 0.0)
                self._exit_override()
                with self._last_command_lock:
                    self._last_command_time = 0.0  # reset so we only fire once
