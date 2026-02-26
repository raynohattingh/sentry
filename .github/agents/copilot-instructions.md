# sentry Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-25

## Active Technologies
- C++ (Arduino framework), avr-gcc (Arduino IDE ≥ 2.x or PlatformIO) + `SoftwareSerial` (Arduino built-in), `<avr/wdt.h>` (AVR built-in — no external libraries required) (001-arduino-firmware)
- N/A — no persistent memory; step counts reset to zero on power-cycle (001-arduino-firmware)
- Dart 3.x / Flutter 3.x (latest stable) + `flutter_riverpod`, `mqtt_client`, `flutter_map`, `flutter_map_tile_caching`, `drift` (SQLite), `flutter_secure_storage`, `flutter_local_notifications`, `flutter_background_service`, `geolocator`, `http` (001-sentry-mobile-app)
- SQLite via `drift` (alert log); `flutter_secure_storage` (credentials) (001-sentry-mobile-app)

- Python 3.10+ (JetPack 6 container base) + OpenCV 4.x, Ultralytics YOLOv8, Flask, pyserial, paho-mqtt, scipy (001-jetson-core)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.10+ (JetPack 6 container base): Follow standard conventions

## Recent Changes
- 001-sentry-mobile-app: Added Dart 3.x / Flutter 3.x (latest stable) + `flutter_riverpod`, `mqtt_client`, `flutter_map`, `flutter_map_tile_caching`, `drift` (SQLite), `flutter_secure_storage`, `flutter_local_notifications`, `flutter_background_service`, `geolocator`, `http`
- 001-arduino-firmware: Added C++ (Arduino framework), avr-gcc (Arduino IDE ≥ 2.x or PlatformIO) + `SoftwareSerial` (Arduino built-in), `<avr/wdt.h>` (AVR built-in — no external libraries required)

- 001-jetson-core: Added Python 3.10+ (JetPack 6 container base) + OpenCV 4.x, Ultralytics YOLOv8, Flask, pyserial, paho-mqtt, scipy

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
