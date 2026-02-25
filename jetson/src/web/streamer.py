"""Flask MJPEG web stream with HTTP Basic Auth.

The stream thread runs independently of the main control loop.  The frame
buffer is updated by the main loop via ``update_stream_frame()``.

Authentication: HTTP Basic Auth checked on every request.
Credentials: ``config.HUD_USERNAME`` / ``config.HUD_PASSWORD``.

Prefix: ``[WEB]``
"""

from __future__ import annotations

import base64
import functools
import logging
import threading
import time
from typing import Callable

import cv2
from flask import Flask, Response, request

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global frame buffer
# ---------------------------------------------------------------------------

output_frame = None
lock = threading.Lock()

app = Flask(__name__)


def update_stream_frame(frame) -> None:
    """Update the MJPEG broadcast frame.

    Args:
        frame: OpenCV BGR numpy array with HUD overlays applied.
    """
    global output_frame
    with lock:
        output_frame = frame.copy() if frame is not None else None


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def _check_auth(username: str, password: str) -> bool:
    return username == config.HUD_USERNAME and password == config.HUD_PASSWORD


def _unauthorized() -> Response:
    return Response(
        "Unauthorized — Sentry HUD requires HTTP Basic Auth.",
        401,
        {"WWW-Authenticate": 'Basic realm="Sentry HUD"'},
    )


def require_auth(f: Callable) -> Callable:
    """Decorator: enforce HTTP Basic Auth on a Flask route.

    Args:
        f: The route handler to protect.

    Returns:
        Wrapped handler that returns 401 when credentials are invalid.
    """

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not _check_auth(auth.username, auth.password):
            logger.warning("[WEB] Unauthorized access attempt from %s.",
                           request.remote_addr)
            return _unauthorized()
        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Stream generator
# ---------------------------------------------------------------------------


def generate():
    """MJPEG frame generator.

    Yields:
        Multipart JPEG byte chunks for the HTTP response.
    """
    global output_frame
    while True:
        with lock:
            frame = output_frame

        if frame is None:
            time.sleep(0.05)
            continue

        flag, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not flag:
            time.sleep(0.05)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + bytearray(encoded)
            + b"\r\n"
        )
        time.sleep(0.05)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
@require_auth
def index() -> str:
    """Serve the web HUD HTML page."""
    logger.debug("[WEB] HUD page served.")
    return """
    <html>
        <head>
            <title>Sentry HUD</title>
            <style>
                body { background-color: #111; color: #0f0; font-family: monospace; text-align: center; }
                h1 { margin-top: 20px; }
                img { border: 2px solid #0f0; max-width: 100%; height: auto; }
            </style>
        </head>
        <body>
            <h1>SENTRY LIVE FEED</h1>
            <img src="/video_feed">
        </body>
    </html>
    """


@app.route("/video_feed")
@require_auth
def video_feed() -> Response:
    """Stream the MJPEG video feed."""
    logger.debug("[WEB] Video feed started for %s.", request.remote_addr)
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------


def start_web_server(host: str = "0.0.0.0", port: int = 5000) -> None:
    """Start the Flask web server (blocking).

    Intended to be run in a daemon thread from main.py.

    Args:
        host: Bind address.
        port: TCP port.
    """
    logger.info("[WEB] Stream available at http://%s:%d", host, port)
    app.run(host=host, port=port, debug=False, use_reloader=False)
