import cv2
import numpy as np
from ultralytics import YOLO
import time
import os
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any

@dataclass
class DetectionParams:
    # YOLO model parameters
    confidence_threshold: float = 0.5
    vehicle_classes: List[int] = None  # COCO class IDs for vehicles
    
    # Collision detection parameters (optimized for real-time)
    head_on_threshold: float = 0.12
    
    # Display parameters
    head_on_color: Tuple[int, int, int] = (0, 0, 255)    # Red
    safe_color: Tuple[int, int, int] = (0, 255, 0)       # Green
    warning_thickness: int = 3
    safe_thickness: int = 2
    text_scale: float = 0.7
    text_thickness: int = 2
    
    def __post_init__(self):
        if self.vehicle_classes is None:
            self.vehicle_classes = [2, 3, 5, 7]  # COCO class IDs for vehicles

class RealTimeCollisionDetector:
    def __init__(self, model_path='yolov8n.pt', params: DetectionParams = None, 
                 camera_source=0, resolution=(640, 480)):
        # Initialize YOLO model
        self.model = YOLO(model_path)
        self.params = params if params is not None else DetectionParams()
        
        # Initialize camera
        self.cap = cv2.VideoCapture("C:\\Users\\senth\\Downloads\\Collision-main\\Collision-main\\collision 1.mp4")
        if not self.cap.isOpened():
            raise ValueError(f"Could not open camera source: {camera_source}")
        
        # Set camera resolution for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        
        # Performance tracking
        self.frame_count = 0
        self.fps = 0
        self.start_time = time.time()
        
        print(f"Camera initialized with resolution: {resolution}")
        print(f"Model loaded: {model_path}")
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Process a single frame for collision detection"""
        height, width = frame.shape[:2]
        frame_center_x = width // 2
        
        # Run YOLO detection
        results = self.model(frame, verbose=False)
        
        # Collect vehicle detections
        vehicles: List[Dict[str, Any]] = []
        for result in results:
            for box in result.boxes:
                if (int(box.cls[0]) in self.params.vehicle_classes and
                    float(box.conf[0]) > self.params.confidence_threshold):
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    center = ((x1 + x2) // 2, (y1 + y2) // 2)
                    vehicles.append({
                        'box': (x1, y1, x2, y2),
                        'center': center,
                        'class': int(box.cls[0]),
                        'confidence': float(box.conf[0]),
                    })
        
        # If nothing detected, return frame
        if not vehicles:
            return frame, False
        
        # Score each vehicle for "head-on" threat
        best_vehicle = None
        best_score = 0.0
        height_f = float(height)
        width_f = float(width)
        
        for v in vehicles:
            x1, y1, x2, y2 = v['box']
            center_x, center_y = v['center']
            
            # 1) Vertical proximity: closer to the bottom = closer to us
            vertical_proximity = max(0.0, min(1.0, y2 / height_f))
            
            # 2) Horizontal alignment: closer to center = more in our lane
            horizontal_offset = abs(center_x - frame_center_x) / (width_f / 2.0)
            horizontal_alignment = max(0.0, 1.0 - horizontal_offset)
            
            # 3) Size factor: larger box = closer vehicle
            box_area = max(1.0, float((x2 - x1) * (y2 - y1)))
            size_factor = min(1.0, box_area / (width_f * height_f * 0.25))
            
            # Final threat score (0..1)
            threat_score = (0.5 * vertical_proximity + 0.5 * size_factor) * horizontal_alignment
            v['threat_score'] = threat_score
            
            if threat_score > best_score:
                best_score = threat_score
                best_vehicle = v
        
        # Check if best vehicle is a head-on threat
        head_on_warning = False
        if best_vehicle is not None:
            bx1, by1, bx2, by2 = best_vehicle['box']
            b_center_x, b_center_y = best_vehicle['center']
            
            vertical_proximity = max(0.0, min(1.0, by2 / height_f))
            horizontal_offset = abs(b_center_x - frame_center_x) / (width_f / 2.0)
            horizontal_alignment = max(0.0, 1.0 - horizontal_offset)
            box_area = max(1.0, float((bx2 - bx1) * (by2 - by1)))
            size_factor = min(1.0, box_area / (width_f * height_f * 0.25))
            
            if (
                best_score >= self.params.head_on_threshold
                and vertical_proximity > 0.3
                and horizontal_alignment > 0.35
                and size_factor > 0.06
            ):
                head_on_warning = True
        
        # Draw all vehicles: best one in RED if threat, others in GREEN
        for v in vehicles:
            x1, y1, x2, y2 = v['box']
            label_base = self.model.names[v['class']]
            conf = v['confidence']
            
            if v is best_vehicle and head_on_warning:
                color = self.params.head_on_color
                thickness = self.params.warning_thickness
                label = f"HEAD-ON RISK: {label_base} {conf:.2f}"
                text_color = (0, 0, 255)
            else:
                color = self.params.safe_color
                thickness = self.params.safe_thickness
                label = f"{label_base} {conf:.2f}"
                text_color = self.params.safe_color
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            cv2.putText(
                frame,
                label,
                (x1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                self.params.text_scale,
                text_color,
                self.params.text_thickness,
            )
        
        # Add warning text if head-on detected
        if head_on_warning and best_vehicle is not None:
            warning_text = "WARNING: VEHICLE AHEAD - POTENTIAL COLLISION"
            text_size = cv2.getTextSize(
                warning_text,
                cv2.FONT_HERSHEY_SIMPLEX,
                self.params.text_scale * 1.2,
                self.params.text_thickness * 2,
            )[0]
            text_x = (width - text_size[0]) // 2
            
            # Background for better text visibility
            cv2.rectangle(
                frame,
                (text_x - 10, 30 - text_size[1] - 10),
                (text_x + text_size[0] + 10, 50),
                (0, 0, 0),
                -1,
            )
            
            # Warning text
            cv2.putText(
                frame,
                warning_text,
                (text_x, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                self.params.text_scale * 1.2,
                self.params.head_on_color,
                self.params.text_thickness * 2,
                cv2.LINE_AA,
            )
            
            # Red border to emphasize danger
            border_size = 10
            frame[0:border_size, :] = self.params.head_on_color  # Top
            frame[-border_size:, :] = self.params.head_on_color  # Bottom
            frame[:, 0:border_size] = self.params.head_on_color  # Left
            frame[:, -border_size:] = self.params.head_on_color  # Right
        
        return frame, head_on_warning
    
    def run(self):
        """Main loop for real-time detection"""
        print("Starting real-time collision detection...")
        print("Press 'q' to quit")
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to capture frame")
                    break
                
                # Process frame
                processed_frame, warning = self.process_frame(frame)
                
                # Calculate FPS
                self.frame_count += 1
                if self.frame_count % 10 == 0:
                    elapsed = time.time() - self.start_time
                    self.fps = self.frame_count / elapsed if elapsed > 0 else 0
                    print(f"FPS: {self.fps:.1f} | Warnings: {'Yes' if warning else 'No'}")
                
                # Add FPS display
                cv2.putText(
                    processed_frame,
                    f"FPS: {self.fps:.1f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )
                
                # Show frame
                cv2.imshow('Collision Detection', processed_frame)
                
                # Exit on 'q' key
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
        except KeyboardInterrupt:
            print("\nStopping detection...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.cap.release()
        cv2.destroyAllWindows()
        print("Resources cleaned up")

def main():
    # Configuration for Raspberry Pi
    params = DetectionParams(
        confidence_threshold=0.5,
        head_on_threshold=0.12,
        text_scale=0.7,
    )
    
    # Try different camera sources
    camera_sources = [0, 1, 2]  # Try different camera indices
    
    for source in camera_sources:
        try:
            print(f"Trying camera source: {source}")
            detector = RealTimeCollisionDetector(
                model_path='yolov8n.pt',
                params=params,
                camera_source=source,
                resolution=(640, 480)  # Lower resolution for better performance
            )
            detector.run()
            break
        except ValueError as e:
            print(f"Camera source {source} failed: {e}")
            continue
    else:
        print("No camera found. Please check your camera connection.")

if __name__ == "__main__":
    main()
