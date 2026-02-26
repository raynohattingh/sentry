# Quickstart: Farm Sentry Mobile App

**Branch**: `001-sentry-mobile-app`

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Flutter SDK | ≥ 3.22 (stable channel) | [flutter.dev/docs/get-started](https://flutter.dev/docs/get-started/install) |
| Dart SDK | ≥ 3.4 (bundled with Flutter) | — |
| Xcode | ≥ 15 (macOS only, for iOS builds) | App Store |
| Android Studio | ≥ 2024.1 | [developer.android.com/studio](https://developer.android.com/studio) |
| CocoaPods | ≥ 1.15 (macOS only) | `sudo gem install cocoapods` |
| A running MQTT broker | Mosquitto ≥ 2.0 with TLS | See broker setup below |

---

## 1 — Clone & Install Dependencies

```bash
# From repo root
cd app
flutter pub get
```

For iOS, also run:
```bash
cd ios && pod install && cd ..
```

---

## 2 — Broker Setup (Development)

The app requires a TLS-enabled MQTT broker. For local development:

```bash
# Generate self-signed cert (dev only — NOT for production)
openssl req -new -x509 -days 365 -keyout broker.key -out broker.crt -nodes

# Mosquitto config snippet (mosquitto.conf)
listener 8883
certfile /path/to/broker.crt
keyfile  /path/to/broker.key
require_certificate false
password_file /path/to/passwd
allow_anonymous false

# Create credentials
mosquitto_passwd -c /path/to/passwd <username>
```

> **Note**: For development against a self-signed cert, temporarily set `onBadCertificate: (cert) => true` in `MqttServiceImpl`. This flag MUST be `false` in production builds.

---

## 3 — Run on a Device / Emulator

```bash
# List available devices
flutter devices

# Run on specific device (debug)
flutter run -d <device-id>

# Run on iOS simulator
flutter run -d "iPhone 15 Pro"

# Run on Android emulator
flutter run -d emulator-5554
```

---

## 4 — First-Launch Setup

On first launch the app presents the **Setup Flow**. Enter:

| Field | Value | Notes |
|---|---|---|
| **MQTT Broker Host** | `192.168.x.x` or hostname | IP of your broker machine |
| **MQTT Port** | `8883` | TLS port (1883 rejected) |
| **MQTT Username** | as configured in `passwd` | |
| **MQTT Password** | as configured in `passwd` | |
| **Sentry ID** | `farm-sentry-01` (or any string) | Used as MQTT client ID suffix |
| **Video Stream Host** | `192.168.x.x` or hostname | Defaults to broker host |
| **Video Stream Port** | `5000` | Flask default |
| **Video Username** | as configured in Flask | |
| **Video Password** | as configured in Flask | |

After setup, navigate to **Settings → Calibration** to pin the sentry's GPS coordinates and set the True North offset.

---

## 5 — Run Tests

```bash
# All tests
flutter test

# Unit tests only
flutter test test/unit/

# With coverage
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
```

---

## 6 — Build Release

```bash
# Android APK
flutter build apk --release

# Android App Bundle (Play Store)
flutter build appbundle --release

# iOS (requires macOS + Xcode + signing)
flutter build ios --release
```

---

## 7 — Simulate Telemetry (Development)

Use the provided MQTT test script to inject mock telemetry without a live sentry:

```bash
# From repo root
python3 test/mqtt_sim.py \
  --broker 192.168.x.x \
  --port 8883 \
  --username <user> \
  --password <pass> \
  --tier HIGH \
  --lat -26.204103 \
  --lon 28.047305
```

> **Note**: `test/mqtt_sim.py` is a development utility to be created alongside the mobile app. It publishes mock `TelemetryRecord` JSON including `velocity_vector` and `fsm_state` fields.

---

## 8 — Key Configurable Parameters

All constants live in `lib/core/constants.dart`. Do not hard-code values elsewhere.

| Constant | Default | Description |
|---|---|---|
| `kDefaultMqttPort` | `8883` | Default TLS MQTT port |
| `kDefaultVideoPort` | `5000` | Flask MJPEG stream port |
| `kHeartbeatTimeoutSec` | `10` | Seconds without telemetry → Offline state |
| `kMarkerFadeRemovalSec` | `30` | Seconds after fade starts → marker removed |
| `kJoystickPublishIntervalMs` | `100` | Milliseconds between joystick MQTT commands (10 Hz) |
| `kDefaultRetentionDuration` | `7 days` | Default alert log retention |
| `kThreatTierMedThreshold` | `40.0` | LOW/MED boundary (matches backend config.py) |
| `kThreatTierHighThreshold` | `80.0` | MED/HIGH boundary (matches backend config.py) |
| `kMaxJoystickVelocity` | `200.0` | Max steps/sec for pan/tilt commands |

---

## 9 — iOS Critical Alert Entitlement (Production)

To enable HIGH-tier alarms that override iOS Do Not Disturb (FR-014), the production app requires Apple's **Critical Alert** entitlement. Request via:
[developer.apple.com/contact/request/notifications-critical-alerts-entitlement](https://developer.apple.com/contact/request/notifications-critical-alerts-entitlement)

Without this entitlement, HIGH-tier alarms on iOS play at normal notification volume and are silenced by DND. All other notification behaviour is unaffected.
