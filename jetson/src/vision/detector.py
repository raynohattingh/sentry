# src/vision/detector.py
from ultralytics import YOLO
import config

class ObjectDetector:
    def __init__(self):
        print(f"[AI] Loading Model: {config.MODEL_PATH}...")
        self.model = YOLO(config.MODEL_PATH)
    
    def detect(self, frame):
        # Run inference
        results = self.model.predict(
            frame, 
            conf=config.CONF_THRESHOLD, 
            classes=[config.TARGET_CLASS_ID], 
            verbose=False
        )
        
        # Parse results for the largest target
        best_target = None
        max_area = 0

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                area = (x2 - x1) * (y2 - y1)
                
                if area > max_area:
                    max_area = area
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    best_target = {
                        "cx": cx, "cy": cy,
                        "bbox": (x1, y1, x2, y2)
                    }
                    
        return best_target