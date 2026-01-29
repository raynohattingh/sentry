import cv2
import threading
import time
import config

class CameraStream:
    def __init__(self):
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        self.cap = None

        # --- METHOD 1: GStreamer (Low Latency) ---
        if config.USE_GSTREAMER:
            print(f"[CAM] Attempting GStreamer Pipeline...")
            try:
                self.cap = cv2.VideoCapture(config.GST_PIPELINE, cv2.CAP_GSTREAMER)
            except Exception as e:
                print(f"[CAM] GStreamer Error: {e}")

        # --- METHOD 2: Fallback to Standard V4L2 ---
        if self.cap is None or not self.cap.isOpened():
            print("[CAM] GStreamer failed or not configured. Switching to Standard V4L2 Driver...")
            
            # Index 0 usually maps to /dev/video0
            # cv2.CAP_V4L2 ensures we don't try FFMPEG or other backends
            self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
            
            # Force the parameters manually for the standard driver
            # This replicates what the GStreamer pipeline was trying to do
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 320)
            
            # Force Raw Mode (YUYV) to avoid MJPEG lag
            # This spells 'YUYV' in ASCII integer for the FourCC code
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))

        # --- FINAL CHECK ---
        if not self.cap.isOpened():
            # If we get here, the camera is likely unplugged or busy
            print("[CAM] CRITICAL FAILURE: Could not open any video source.")
            print("[CAM] Hint: Check if another process (like gst-launch) is still running.")
            raise RuntimeError("Could not open video source")
        
        print(f"[CAM] Success! Video Backend: {self.cap.getBackendName()}")

    def start(self):
        self.running = True
        t = threading.Thread(target=self._update)
        t.daemon = True
        t.start()
        return self

    def _update(self):
        while self.running:
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.frame = frame
                else:
                    # If read fails, wait briefly to prevent CPU spam
                    time.sleep(0.01)
            else:
                time.sleep(0.1)

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()