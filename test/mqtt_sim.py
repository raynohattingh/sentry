#!/usr/bin/env python3
"""
MQTT Telemetry Simulation Script for Farm Sentry mobile app.

Publishes TelemetryRecord JSON matching contracts/mqtt-telemetry-inbound.md
to the sentry/telemetry topic over TLS MQTT.

Usage:
    python mqtt_sim.py \\
        --broker 192.168.1.100 \\
        --port 8883 \\
        --username admin \\
        --password secret \\
        --tier HIGH \\
        --lat -26.2041 \\
        --lon 28.0473 \\
        --fsm-state TRACK \\
        --vx 1.5 \\
        --vy -0.5 \\
        --count 10 \\
        --interval 1.0 \\
        --throttle-kbps 50

Throttle flag simulates SC-003 EDGE/3G conditions (~50 kbps).
"""

import argparse
import json
import ssl
import time
import uuid
from datetime import datetime, timezone

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("ERROR: paho-mqtt not installed. Run: pip install paho-mqtt")
    raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Farm Sentry MQTT telemetry simulator"
    )
    parser.add_argument("--broker", required=True, help="MQTT broker host/IP")
    parser.add_argument("--port", type=int, default=8883, help="MQTT broker port (default: 8883)")
    parser.add_argument("--username", required=True, help="MQTT username")
    parser.add_argument("--password", required=True, help="MQTT password")
    parser.add_argument(
        "--tier",
        default="MED",
        choices=["LOW", "MED", "HIGH"],
        help="Threat tier (default: MED)",
    )
    parser.add_argument("--target-id", type=int, default=1, help="Target ID (default: 1)")
    parser.add_argument("--threat-score", type=float, default=55.0, help="Threat score 0-100")
    parser.add_argument("--lat", type=float, default=None, help="Latitude (optional)")
    parser.add_argument("--lon", type=float, default=None, help="Longitude (optional)")
    parser.add_argument("--lrf-distance", type=float, default=None, help="LRF distance in metres")
    parser.add_argument("--pan-angle", type=float, default=0.0, help="Pan angle degrees")
    parser.add_argument("--tilt-angle", type=float, default=0.0, help="Tilt angle degrees")
    parser.add_argument(
        "--fsm-state",
        default=None,
        choices=["SCAN", "ACQUIRE", "TRACK", "SEARCH", None],
        help="FSM state (optional)",
    )
    parser.add_argument("--vx", type=float, default=None, help="Velocity X component")
    parser.add_argument("--vy", type=float, default=None, help="Velocity Y component")
    parser.add_argument("--count", type=int, default=1, help="Number of messages to send (default: 1)")
    parser.add_argument(
        "--interval", type=float, default=1.0, help="Interval between messages in seconds"
    )
    parser.add_argument(
        "--throttle-kbps",
        type=float,
        default=None,
        help="Simulate bandwidth limit in kbps (SC-003 EDGE/3G test). "
             "Uses token-bucket sleep loop.",
    )
    parser.add_argument(
        "--no-tls",
        action="store_true",
        help="Disable TLS (for local testing without certs)",
    )
    return parser.parse_args()


def build_payload(args: argparse.Namespace, session_id: str, seq: int) -> dict:
    """Build a TelemetryRecord matching contracts/mqtt-telemetry-inbound.md."""
    payload: dict = {
        "session_id": session_id,
        "target_id": args.target_id,
        "threat_score": args.threat_score,
        "tier": args.tier,
        "lat": args.lat,
        "lon": args.lon,
        "lrf_distance_m": args.lrf_distance,
        "pan_angle": args.pan_angle + seq * 0.1,  # slight variation per message
        "tilt_angle": args.tilt_angle,
        "timestamp_utc": datetime.now(tz=timezone.utc).isoformat(),
        "velocity_vector": None,
        "fsm_state": args.fsm_state,
    }
    if args.vx is not None and args.vy is not None:
        payload["velocity_vector"] = {"vx": args.vx, "vy": args.vy}
    return payload


def throttle_sleep(payload_bytes: int, throttle_kbps: float) -> None:
    """Token-bucket sleep to simulate bandwidth limit (SC-003)."""
    payload_kbits = (payload_bytes * 8) / 1000.0
    required_seconds = payload_kbits / throttle_kbps
    if required_seconds > 0:
        time.sleep(required_seconds)


def main() -> None:
    args = parse_args()
    session_id = str(uuid.uuid4())
    client_id = f"mqtt_sim_{uuid.uuid4().hex[:8]}"

    print(f"[SIM] Connecting to {args.broker}:{args.port} as {args.username}")
    print(f"[SIM] Session ID: {session_id}")
    print(f"[SIM] Tier: {args.tier} | Target: {args.target_id} | Count: {args.count}")
    if args.throttle_kbps:
        print(f"[SIM] Throttle: {args.throttle_kbps} kbps (SC-003 test mode)")

    client = mqtt.Client(client_id=client_id)
    client.username_pw_set(args.username, args.password)

    if not args.no_tls:
        tls_ctx = ssl.create_default_context()
        tls_ctx.check_hostname = False
        tls_ctx.verify_mode = ssl.CERT_NONE  # Use CERT_REQUIRED in production
        client.tls_set_context(tls_ctx)

    try:
        client.connect(args.broker, args.port, keepalive=30)
        client.loop_start()
        time.sleep(0.5)  # Allow connection to establish

        for i in range(args.count):
            payload = build_payload(args, session_id, i)
            payload_json = json.dumps(payload)
            payload_bytes = payload_json.encode("utf-8")

            result = client.publish(
                "sentry/telemetry",
                payload_json,
                qos=1,
            )
            result.wait_for_publish(timeout=5.0)

            print(
                f"[SIM] [{i+1}/{args.count}] Published {len(payload_bytes)} bytes | "
                f"tier={args.tier} score={args.threat_score:.1f} "
                f"lat={args.lat} lon={args.lon} fsm={args.fsm_state}"
            )

            if args.throttle_kbps:
                throttle_sleep(len(payload_bytes), args.throttle_kbps)

            if i < args.count - 1:
                time.sleep(args.interval)

        client.loop_stop()
        client.disconnect()
        print(f"[SIM] Done — {args.count} message(s) published.")

    except ConnectionRefusedError:
        print(f"ERROR: Connection refused to {args.broker}:{args.port}")
        raise
    except Exception as e:
        print(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
