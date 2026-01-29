# src/main.py
import cv2
import time
import threading
from vision.camera import CameraStream
from vision.detector import ObjectDetector
from control.turret_manager import TurretManager
from web.streamer import start_web_server, update_stream_frame

def main():
    # 1. Initialize Subsystems
    camera = CameraStream().start()
    detector = ObjectDetector()
    turret = TurretManager()

    # 2. Start Web Stream (Optional, runs in background)
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()

    print("[SYSTEM] Sentry Core Online.")

    try:
        while True:
            # A. Get Frame
            frame = camera.read()
            if frame is None:
                continue

            # B. Detect Threats
            target = detector.detect(frame)

            # C. Move Turret
            err, vel = turret.track(target)

            # D. Visual Feedback (Overlay)
            if target:
                x1, y1, x2, y2 = target["bbox"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(frame, f"ERR: {err} V: {vel:.0f}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "SCANNING...", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

            # E. Update Web Stream
            update_stream_frame(frame)
            
            # F. Yield control briefly
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("[SYSTEM] Shutting down...")
        turret.stop()
        camera.stop()

if __name__ == "__main__":
    main()