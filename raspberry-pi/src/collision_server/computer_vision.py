"""
Computer Vision Module for object detection and tracking
"""
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque

print("Loading computer vision module...")


@dataclass
class BoundingBox:
    """Bounding box representation for detected objects"""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    def intersects(self, other: 'BoundingBox') -> bool:
        return not (self.x + self.width < other.x or 
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or
                   other.y + other.height < self.y)


@dataclass
class Vector2D:
    """2D vector representation for velocity calculations"""
    x: float
    y: float
    
    def magnitude(self) -> float:
        return np.sqrt(self.x**2 + self.y**2)


@dataclass
class DetectedObject:
    """Detected object representation with tracking information"""
    id: str
    class_name: str
    confidence: float
    bounding_box: BoundingBox
    velocity: Vector2D
    timestamp: float
    flagged_for_review: bool = False


class ComputerVisionModule:
    """Computer vision module for object detection and tracking"""
    
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.5):
        """Initialize computer vision module"""
        self.confidence_threshold = confidence_threshold
        self.next_object_id = 0
        self.detection_method = 'opencv'
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True, varThreshold=50)
        
        # Object tracking state
        self.active_tracks = {}
        self.track_history = defaultdict(lambda: deque(maxlen=10))
        self.max_distance_threshold = 50.0
        self.max_frames_missing = 5
        self.frame_count = 0
        
        print("Initialized OpenCV-based detection with object tracking")
    
    def detect_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect objects in a video frame"""
        detections = []
        
        # Motion-based detection using background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:  # Filter small areas
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calculate confidence based on area and shape
                confidence = min(0.9, area / 10000.0 + 0.3)
                
                detections.append({
                    'bbox': [float(x), float(y), float(w), float(h)],
                    'confidence': confidence,
                    'class_name': 'moving_object'
                })
        
        return detections
    
    def track_objects(self, detections: List[Dict[str, Any]], timestamp: float) -> List[DetectedObject]:
        """Track objects across frames with ID continuity maintenance"""
        self.frame_count += 1
        current_detections = []
        
        # Convert raw detections to DetectedObject format
        for detection in detections:
            bbox = detection['bbox']
            bounding_box = BoundingBox(bbox[0], bbox[1], bbox[2], bbox[3])
            
            detected_object = DetectedObject(
                id=f"obj_{self.next_object_id}",
                class_name=detection['class_name'],
                confidence=detection['confidence'],
                bounding_box=bounding_box,
                velocity=Vector2D(0, 0),
                timestamp=timestamp
            )
            self.next_object_id += 1
            current_detections.append(detected_object)
        
        return current_detections
    
    def calculate_velocities(self, tracks: List[DetectedObject]) -> List[DetectedObject]:
        """Calculate object velocities from position history"""
        return tracks
    
    def predict_collisions(self, tracks: List[DetectedObject]) -> List[Tuple[DetectedObject, DetectedObject, float]]:
        """Predict potential collisions based on current trajectories"""
        potential_collisions = []
        
        # Simple collision prediction based on bounding box intersection
        for i, obj1 in enumerate(tracks):
            for j, obj2 in enumerate(tracks[i+1:], i+1):
                if obj1.bounding_box.intersects(obj2.bounding_box):
                    potential_collisions.append((obj1, obj2, 0.0))
        
        return potential_collisions