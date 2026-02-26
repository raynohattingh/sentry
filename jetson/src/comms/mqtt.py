"""Non-blocking MQTT publisher.

Uses a daemon thread + queue.Queue so that ``publish_async()`` never blocks
the main control loop.  If the broker is unavailable the queue fills up and
overflow is silently dropped with a ``[MQTT] Queue full`` log message.

MQTT failures never propagate to the caller.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Protocol, runtime_checkable

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
        """Establish a connection to the MQTT broker."""
        try:
            import paho.mqtt.client as mqtt  # type: ignore[import]
        except ImportError:
            logger.error("[MQTT] paho-mqtt not installed — MQTT disabled.")
            time.sleep(60)
            return

        client = mqtt.Client()
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
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
                    # Re-queue if not connected (will be retried on reconnect).
                    try:
                        self._queue.put_nowait(payload)
                    except queue.Full:
                        pass
                    time.sleep(0.5)
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
