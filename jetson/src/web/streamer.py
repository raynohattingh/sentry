import cv2
import threading
import time
from flask import Flask, Response

# --- GLOBAL STATE ---
# We use a global variable to store the latest frame.
# The 'lock' ensures that we don't try to read the frame 
# while it's being written to by the main thread.
output_frame = None
lock = threading.Lock()

# Initialize Flask App
app = Flask(__name__)

def update_stream_frame(frame):
    """
    Called by the Main Loop to update the image being broadcast.
    frame: The OpenCV image (numpy array) with overlays drawn.
    """
    global output_frame
    with lock:
        # We copy the frame to prevent reference issues if the 
        # main loop modifies it immediately after.
        output_frame = frame.copy()

def generate():
    """
    Generator function that encodes the frame as JPEG and streams it.
    This creates the Motion JPEG (MJPEG) standard used by IP cameras.
    """
    global output_frame
    
    while True:
        with lock:
            if output_frame is None:
                continue
            
            # Encode frame to JPEG
            # quality=80 is a good balance of speed vs visual clarity
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            
            if not flag:
                continue

        # Yield the byte stream in the standard multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
        
        # Limit the stream framerate slightly to save bandwidth on 3G/Edge
        # 0.05s delay = ~20 FPS max
        time.sleep(0.05)

@app.route("/")
def index():
    """Renders a simple HTML viewer"""
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
def video_feed():
    """Route that the <img> tag points to"""
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

def start_web_server(host="0.0.0.0", port=5000):
    """
    Starts the Flask server.
    Blocking call - this is meant to be run in a separate thread.
    """
    # debug=False is critical! debug=True causes Flask to spawn a 
    # secondary reloader thread which breaks the camera access.
    print(f"[WEB] Stream available at http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)