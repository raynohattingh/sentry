# Quickstart: Sentry Jetson Core

**Branch**: `001-jetson-core` | **Date**: 2026-02-25

---

## Prerequisites

- NVIDIA Jetson Orin Nano Super with JetPack 6 (Ubuntu 22.04)
- Docker with NVIDIA container runtime (`nvidia-container-toolkit` installed)
- Arduino flashed with Sentry firmware and connected via USB
- Thermal camera (CVBS→USB) connected on `/dev/video0`
- YOLOv8n TensorRT engine pre-exported (`yolov8n.engine`) or PyTorch weights (`yolov8n.pt`)

---

## Repository Layout

```
jetson/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yaml
├── requirements.txt
└── src/
    ├── main.py
    ├── config.py
    └── ...
```

---

## 1. Configure

Edit `jetson/src/config.py` (or set environment variables in `docker-compose.yaml`):

```python
# Minimum required changes for your deployment
SERIAL_PORT = '/dev/ttyUSB0'   # or ttyACM0 — check: ls /dev/tty*
SENTRY_LAT  = -26.123456       # Your GPS latitude
SENTRY_LON  = 28.567890        # Your GPS longitude
HUD_PASSWORD = 'your-password' # Change from default
```

All configurable parameters are documented in
[`specs/001-jetson-core/contracts/config-schema.md`](./contracts/config-schema.md).

---

## 2. Build and Run

```bash
cd jetson/
docker compose -f docker/docker-compose.yaml up --build
```

The container will:
1. Install Python dependencies from `requirements.txt`
2. Start the main loop: camera → inference → FSM → serial → telemetry
3. Serve the web HUD at `http://<jetson-ip>:5000`

---

## 3. Access the HUD

Open a browser on the local network:

```
http://<jetson-ip>:5000
```

- Enter the configured `HUD_USERNAME` / `HUD_PASSWORD` when prompted.
- The MJPEG stream shows live thermal frames with detection overlays.
- Overlay legend:
  - 🔴 Red box = active threat (TRACK / ACQUIRE)
  - 🟢 Green text = status / metadata (FPS, FSM state, target ID)
  - 🟡 Yellow text = warnings (`[TURRET] Approaching limit`, etc.)

---

## 4. Monitor Telemetry

**Local log** (JSON-lines, rotated):
```bash
docker exec sentry_brain tail -f /app/logs/telemetry.jsonl | python3 -m json.tool
```

**MQTT** (if broker configured):
```bash
mosquitto_sub -h <jetson-ip> -t sentry/telemetry
```

---

## 5. Run Tests

```bash
cd jetson/
pip install -r requirements.txt
pytest tests/ -v
```

Tests run entirely without hardware (mock serial, mock camera, mock MQTT).

---

## 6. Disable LRF Mode (Vision-Only)

In `config.py`:
```python
LRF_ENABLED = False
```

The system runs in vision + tracking mode. GPS fields in telemetry will be `null`.
The startup log will show: `[LRF] Disabled — running in vision-only mode`.

---

## 7. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `[SYSTEM] FATAL — TensorRT inference failed` | Engine built on different JetPack | Re-export `.engine` on this Jetson |
| `[CAMERA] Disconnected — retrying` | USB cable loose | Reconnect cable; system auto-recovers |
| `[SERIAL] Disconnected — retrying` | Arduino unplugged or wrong port | Check `SERIAL_PORT` in config |
| `[SERIAL] Malformed frame discarded` | Arduino debug output mixed in | Update Arduino firmware to suppress debug prints |
| `[TURRET] Approaching limit` | Turret near mechanical stop | Normal; turret will decelerate automatically |
| HUD shows 401 | Wrong credentials | Check `HUD_USERNAME` / `HUD_PASSWORD` in config |
| Loop FPS < 18 | GPU overloaded or wrong model | Confirm TRT `.engine` is in use; check GPU utilisation |

---

## 8. Container Restart Behaviour

The container restarts automatically on crash (`restart: unless-stopped`). If it crashes
`MAX_BOOT_FAILURES` consecutive times (default: 3), the system triggers a Jetson OS reboot
to recover from GPU-level faults. After a successful start, the failure counter resets.

Boot state is persisted at `BOOT_STATE_PATH` (default: `/app/state/boot_state.json`).

---

## Troubleshooting

### Boot Failure Counter

The system tracks consecutive TensorRT initialisation failures in
`/app/state/boot_state.json`:

```json
{
  "consecutive_failures": 0,
  "last_failure_utc": null
}
```

If the counter reaches `MAX_BOOT_FAILURES` (default: 3), the Jetson OS is
rebooted automatically via `sudo reboot`. Ensure the `sentry` user has
passwordless `sudo reboot` permission:

```
# /etc/sudoers.d/sentry-reboot
sentry ALL=(ALL) NOPASSWD: /sbin/reboot
```

The counter resets to 0 on every successful main-loop entry.

### Prerequisites

Before deploying, ensure the following are installed on the Jetson:

1. **NVIDIA Container Toolkit**:
   ```bash
   sudo apt-get install -y nvidia-container-toolkit
   sudo systemctl restart docker
   ```

2. **Export the TensorRT engine** (run on the Jetson, not cross-compile):
   ```bash
   yolo export model=yolov8n.pt format=engine device=0
   cp yolov8n.engine jetson/src/
   ```

3. **JetPack version**: This project requires JetPack 6 (Ubuntu 22.04 +
   CUDA 12.2). Pin your base image:
   ```yaml
   image: ultralytics/ultralytics:8.3.x-jetson-jetpack6
   ```

4. **Serial port permissions**:
   ```bash
   sudo usermod -aG dialout $USER
   ```
