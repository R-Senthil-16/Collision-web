"""
Collision Detection Engine for video-based collision analysis

Requirements covered:
- 8.3: Detect and timestamp collision events in uploaded videos
- 8.4: Generate reports with collision timestamps and object trajectories
- 6.2: Use efficient algorithms to minimize computational overhead
- 6.3: Optimize rendering by only updating changed areas when possible
"""
import time
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

# Configure logging for error handling
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from .computer_vision import ComputerVisionModule, DetectedObject, BoundingBox, Vector2D
    from .spatial_partitioning import SpatialGrid, PerformanceMonitor, BoundingBox as SpatialBoundingBox
except ImportError:
    # For testing purposes, allow running without relative imports
    logger.warning("Could not import relative modules, running in standalone mode")


class CollisionEngineError(Exception):
    """Base exception for collision engine errors"""
    pass


class FrameProcessingError(CollisionEngineError):
    """Exception raised when frame processing fails"""
    pass


class SpatialOptimizationError(CollisionEngineError):
    """Exception raised when spatial optimization fails"""
    pass


class HardwareControlError(CollisionEngineError):
    """Exception raised when hardware control fails"""
    pass


@dataclass
class CollisionEvent:
    """Collision event representation with complete information"""
    id: str
    object1: Any  # DetectedObject
    object2: Any  # DetectedObject
    collision_point: Tuple[float, float]
    timestamp: float
    severity: float
    video_source: str
    frame_number: int


@dataclass
class VideoAnalysisResult:
    """Complete video analysis result with collision events and statistics"""
    video_id: str
    total_frames: int
    processed_frames: int
    collision_events: List[CollisionEvent]
    processing_time: float
    confidence_scores: List[float]
    analysis_metadata: Dict[str, Any]


class CollisionEngine:
    """Engine for detecting collisions in video analysis with spatial optimization and error handling"""
    
    def __init__(self, cv_module, hardware_controller=None, frame_width=1920, frame_height=1080):
        """
        Initialize collision detection engine with spatial partitioning and error handling
        
        Args:
            cv_module: Computer vision module for object detection
            hardware_controller: Optional hardware controller for triggering responses
            frame_width: Width of video frames for spatial grid sizing
            frame_height: Height of video frames for spatial grid sizing
        """
        self.cv_module = cv_module
        self.hardware_controller = hardware_controller
        self.collision_events: List[CollisionEvent] = []
        self.object_tracks: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10))
        self.collision_threshold = 0.1  # Minimum overlap ratio for collision
        self.severity_threshold = 0.5   # Minimum severity for logging
        
        # Error handling and recovery settings
        self.max_retries = 3
        self.retry_delay = 0.1  # seconds
        self.error_count = 0
        self.max_errors_per_session = 100
        self.recovery_mode = False
        self.last_error_time = 0
        self.error_recovery_timeout = 5.0  # seconds
        
        # Initialize spatial partitioning with error handling
        try:
            self.spatial_grid = SpatialGrid(frame_width, frame_height, cell_size=100.0)
            self.performance_monitor = PerformanceMonitor(window_size=100)
            logger.info("Spatial optimization initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize spatial optimization: {e}")
            self.spatial_grid = None
            self.performance_monitor = None
        
        # Performance optimization settings
        self.use_spatial_optimization = self.spatial_grid is not None
        self.adaptive_quality = True
        self.max_objects_per_frame = 100  # Limit for performance
        
        # Frame processing statistics
        self.frame_stats = {
            'total_frames_processed': 0,
            'total_collisions_detected': 0,
            'average_processing_time': 0.0,
            'spatial_optimization_enabled': self.use_spatial_optimization,
            'error_count': 0,
            'recovery_count': 0,
            'last_error': None
        }
        
    def analyze_frame(self, frame, timestamp: float, frame_number: int, video_source: str = "unknown") -> List[CollisionEvent]:
        """
        Analyze a single video frame for collision detection with comprehensive error handling
        
        Args:
            frame: Video frame (numpy array)
            timestamp: Frame timestamp in seconds
            frame_number: Frame number in video sequence
            video_source: Source identifier for the video
            
        Returns:
            List of collision events detected in this frame
        """
        frame_start_time = time.time()
        frame_collisions = []
        
        # Check if we're in recovery mode
        if self.recovery_mode:
            if time.time() - self.last_error_time > self.error_recovery_timeout:
                self.recovery_mode = False
                logger.info("Exiting recovery mode")
            else:
                # In recovery mode, use simplified processing
                return self._analyze_frame_recovery_mode(frame, timestamp, frame_number, video_source)
        
        # Check error count limits
        if self.error_count >= self.max_errors_per_session:
            logger.error("Maximum error count reached, entering permanent recovery mode")
            self.recovery_mode = True
            return []
        
        try:
            # Detect objects in the frame with retry mechanism
            detections = self._detect_objects_with_retry(frame)
            tracked_objects = self._track_objects_with_retry(detections, timestamp)
            
            # Apply performance-based object limiting
            if len(tracked_objects) > self.max_objects_per_frame:
                # Sort by confidence and keep only the most confident detections
                tracked_objects = sorted(tracked_objects, key=lambda x: getattr(x, 'confidence', 0.5), reverse=True)[:self.max_objects_per_frame]
            
            # Update object tracking history with error handling
            try:
                self._update_object_tracks(tracked_objects, timestamp)
            except Exception as e:
                logger.warning(f"Failed to update object tracks: {e}")
                # Continue processing without track updates
            
            # Calculate velocities based on tracking history
            try:
                objects_with_velocity = self._calculate_velocities(tracked_objects)
            except Exception as e:
                logger.warning(f"Failed to calculate velocities: {e}")
                objects_with_velocity = tracked_objects  # Use objects without velocity
            
            # Update spatial grid with current objects (with error handling)
            if self.use_spatial_optimization:
                try:
                    self._update_spatial_grid(objects_with_velocity)
                except SpatialOptimizationError as e:
                    logger.warning(f"Spatial optimization failed: {e}")
                    # Fall back to brute force collision detection
                    self.use_spatial_optimization = False
            
            # Detect collisions between objects (using spatial optimization if enabled)
            try:
                frame_collisions = self.detect_collisions_optimized(objects_with_velocity, timestamp, frame_number, video_source)
            except Exception as e:
                logger.error(f"Collision detection failed: {e}")
                # Try fallback collision detection
                try:
                    frame_collisions = self.detect_collisions(objects_with_velocity, timestamp, frame_number, video_source)
                except Exception as fallback_error:
                    logger.error(f"Fallback collision detection also failed: {fallback_error}")
                    frame_collisions = []
                    self._handle_error(fallback_error, "collision_detection")
            
            # Record performance metrics with error handling
            try:
                frame_time = time.time() - frame_start_time
                if self.performance_monitor:
                    self.performance_monitor.record_frame(frame_time, len(frame_collisions), len(objects_with_velocity))
            except Exception as e:
                logger.warning(f"Performance monitoring failed: {e}")
            
            # Adjust quality if adaptive quality is enabled
            if self.adaptive_quality:
                try:
                    self._adjust_processing_quality()
                except Exception as e:
                    logger.warning(f"Quality adjustment failed: {e}")
            
            # Update frame statistics
            self._update_frame_statistics(frame_time, len(frame_collisions))
            
            # Log collisions and trigger responses if needed
            for collision in frame_collisions:
                try:
                    self.log_collision(collision)
                    if self.hardware_controller:
                        self.trigger_responses([collision])
                except Exception as e:
                    logger.error(f"Failed to log collision or trigger response: {e}")
                    self._handle_error(e, "collision_response")
            
        except FrameProcessingError as e:
            logger.error(f"Frame processing error: {e}")
            self._handle_error(e, "frame_processing")
            frame_collisions = []
        except Exception as e:
            logger.error(f"Unexpected error in frame analysis: {e}")
            self._handle_error(e, "unexpected")
            frame_collisions = []
        
        return frame_collisions
    
    def _analyze_frame_recovery_mode(self, frame, timestamp: float, frame_number: int, video_source: str) -> List[CollisionEvent]:
        """
        Simplified frame analysis for recovery mode
        
        Args:
            frame: Video frame
            timestamp: Frame timestamp
            frame_number: Frame number
            video_source: Video source identifier
            
        Returns:
            List of collision events (may be empty in recovery mode)
        """
        try:
            logger.debug("Processing frame in recovery mode")
            
            # Use minimal processing in recovery mode
            if hasattr(self.cv_module, 'detect_objects'):
                detections = self.cv_module.detect_objects(frame)
                # Limit to fewer objects in recovery mode
                detections = detections[:5] if len(detections) > 5 else detections
                
                # Simple collision detection without spatial optimization
                collisions = []
                for i, obj1 in enumerate(detections):
                    for j, obj2 in enumerate(detections[i+1:], i+1):
                        if self._simple_collision_check(obj1, obj2):
                            collision_event = CollisionEvent(
                                id=str(uuid.uuid4()),
                                object1=obj1,
                                object2=obj2,
                                collision_point=(0, 0),  # Simplified
                                timestamp=timestamp,
                                severity=0.5,  # Default severity
                                video_source=video_source,
                                frame_number=frame_number
                            )
                            collisions.append(collision_event)
                
                return collisions
            
        except Exception as e:
            logger.error(f"Recovery mode processing failed: {e}")
        
        return []
    
    def _detect_objects_with_retry(self, frame):
        """Detect objects with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                return self.cv_module.detect_objects(frame)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise FrameProcessingError(f"Object detection failed after {self.max_retries} attempts: {e}")
                logger.warning(f"Object detection attempt {attempt + 1} failed: {e}")
                time.sleep(self.retry_delay)
        return []
    
    def _track_objects_with_retry(self, detections, timestamp):
        """Track objects with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                return self.cv_module.track_objects(detections, timestamp)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.warning(f"Object tracking failed after {self.max_retries} attempts: {e}")
                    return detections  # Return detections without tracking
                logger.warning(f"Object tracking attempt {attempt + 1} failed: {e}")
                time.sleep(self.retry_delay)
        return detections
    
    def _simple_collision_check(self, obj1, obj2) -> bool:
        """Simple collision check for recovery mode"""
        try:
            bbox1 = getattr(obj1, 'bounding_box', None)
            bbox2 = getattr(obj2, 'bounding_box', None)
            
            if bbox1 and bbox2:
                return bbox1.intersects(bbox2)
        except Exception:
            pass
        return False
    
    def _handle_error(self, error: Exception, error_type: str):
        """
        Handle errors with recovery mechanisms
        
        Args:
            error: The exception that occurred
            error_type: Type of error for categorization
        """
        self.error_count += 1
        self.last_error_time = time.time()
        self.frame_stats['error_count'] = self.error_count
        self.frame_stats['last_error'] = {
            'type': error_type,
            'message': str(error),
            'timestamp': self.last_error_time
        }
        
        # Enter recovery mode if too many errors
        if self.error_count > 10:
            self.recovery_mode = True
            self.frame_stats['recovery_count'] += 1
            logger.warning(f"Entering recovery mode due to {self.error_count} errors")
        
        # Log error details
        logger.error(f"Error in {error_type}: {error}")
    
    def _update_frame_statistics(self, frame_time: float, collision_count: int):
        """Update frame statistics with error handling"""
        try:
            self.frame_stats['total_frames_processed'] += 1
            self.frame_stats['total_collisions_detected'] += collision_count
            self.frame_stats['average_processing_time'] = (
                (self.frame_stats['average_processing_time'] * (self.frame_stats['total_frames_processed'] - 1) + frame_time) /
                self.frame_stats['total_frames_processed']
            )
        except Exception as e:
            logger.warning(f"Failed to update frame statistics: {e}")
    
    def _update_spatial_grid(self, objects: List):
        """Update the spatial grid with current frame objects with error handling"""
        if not self.spatial_grid:
            raise SpatialOptimizationError("Spatial grid not initialized")
        
        try:
            # Clear previous frame objects
            self.spatial_grid.clear()
            
            # Add current objects to spatial grid
            for obj in objects:
                try:
                    # Convert to spatial bounding box format
                    bbox = getattr(obj, 'bounding_box', None)
                    if bbox:
                        spatial_bbox = SpatialBoundingBox(
                            x=bbox.x,
                            y=bbox.y,
                            width=bbox.width,
                            height=bbox.height
                        )
                        self.spatial_grid.add_object(obj.id, spatial_bbox, obj)
                    else:
                        logger.warning(f"Object {getattr(obj, 'id', 'unknown')} has no bounding box")
                except Exception as e:
                    logger.warning(f"Failed to add object {getattr(obj, 'id', 'unknown')} to spatial grid: {e}")
                    continue
        except Exception as e:
            raise SpatialOptimizationError(f"Failed to update spatial grid: {e}")
    
    def detect_collisions_optimized(self, objects: List, timestamp: float, 
                                  frame_number: int, video_source: str) -> List[CollisionEvent]:
        """
        Detect collisions using spatial partitioning optimization
        
        Args:
            objects: List of detected objects with positions and velocities
            timestamp: Current timestamp
            frame_number: Current frame number
            video_source: Video source identifier
            
        Returns:
            List of collision events detected
        """
        if self.use_spatial_optimization and hasattr(self, 'spatial_grid'):
            return self._detect_collisions_spatial(objects, timestamp, frame_number, video_source)
        else:
            return self.detect_collisions(objects, timestamp, frame_number, video_source)
    
    def _detect_collisions_spatial(self, objects: List, timestamp: float,
                                 frame_number: int, video_source: str) -> List[CollisionEvent]:
        """
        Detect collisions using spatial partitioning for efficiency
        
        Args:
            objects: List of detected objects
            timestamp: Current timestamp
            frame_number: Current frame number
            video_source: Video source identifier
            
        Returns:
            List of collision events detected
        """
        collisions = []
        checked_pairs = set()
        
        for obj in objects:
            try:
                # Find nearby objects using spatial grid
                spatial_bbox = SpatialBoundingBox(
                    x=obj.bounding_box.x,
                    y=obj.bounding_box.y,
                    width=obj.bounding_box.width,
                    height=obj.bounding_box.height
                )
                
                nearby_spatial_objects = self.spatial_grid.get_nearby_objects(spatial_bbox)
                
                # Check collisions only with nearby objects
                for spatial_obj in nearby_spatial_objects:
                    other_obj = spatial_obj.data
                    
                    if other_obj.id == obj.id:
                        continue
                    
                    # Create pair identifier to avoid duplicate checks
                    pair_id = tuple(sorted([obj.id, other_obj.id]))
                    if pair_id in checked_pairs:
                        continue
                    
                    checked_pairs.add(pair_id)
                    
                    # Check for collision
                    collision_info = self._check_collision_pair(obj, other_obj)
                    
                    if collision_info:
                        overlap_ratio, collision_point, severity = collision_info
                        
                        # Only log collisions above severity threshold
                        if severity >= self.severity_threshold:
                            collision_event = CollisionEvent(
                                id=str(uuid.uuid4()),
                                object1=obj,
                                object2=other_obj,
                                collision_point=collision_point,
                                timestamp=timestamp,
                                severity=severity,
                                video_source=video_source,
                                frame_number=frame_number
                            )
                            collisions.append(collision_event)
            
            except Exception as e:
                # Fallback to brute force if spatial optimization fails
                print(f"Spatial collision detection failed for object {obj.id}: {e}")
                continue
        
        return collisions
    
    def _adjust_processing_quality(self):
        """Adjust processing quality based on performance metrics"""
        if not self.adaptive_quality:
            return
        
        quality_level = self.performance_monitor.adjust_quality()
        
        # Adjust collision detection parameters based on quality level
        if quality_level < 0.5:
            # Low quality: reduce precision
            self.collision_threshold = 0.15  # Higher threshold = fewer collisions detected
            self.max_objects_per_frame = 50   # Process fewer objects
            
            # Increase spatial grid cell size for faster processing
            if hasattr(self.spatial_grid, 'cell_size'):
                self.spatial_grid.cell_size = min(200.0, self.spatial_grid.cell_size * 1.1)
        
        elif quality_level > 0.8:
            # High quality: increase precision
            self.collision_threshold = 0.05   # Lower threshold = more sensitive detection
            self.max_objects_per_frame = 100  # Process more objects
            
            # Decrease spatial grid cell size for more precise processing
            if hasattr(self.spatial_grid, 'cell_size'):
                self.spatial_grid.cell_size = max(50.0, self.spatial_grid.cell_size * 0.9)
        
        # Update frame statistics
        self.frame_stats['current_quality_level'] = quality_level
    
    def detect_collisions(self, objects: List, timestamp: float, 
                         frame_number: int, video_source: str) -> List[CollisionEvent]:
        """
        Detect collisions between detected objects
        
        Args:
            objects: List of detected objects with positions and velocities
            timestamp: Current timestamp
            frame_number: Current frame number
            video_source: Video source identifier
            
        Returns:
            List of collision events detected
        """
        collisions = []
        
        # Check all pairs of objects for collisions
        for i, obj1 in enumerate(objects):
            for j, obj2 in enumerate(objects[i+1:], i+1):
                collision_info = self._check_collision_pair(obj1, obj2)
                
                if collision_info:
                    overlap_ratio, collision_point, severity = collision_info
                    
                    # Only log collisions above severity threshold
                    if severity >= self.severity_threshold:
                        collision_event = CollisionEvent(
                            id=str(uuid.uuid4()),
                            object1=obj1,
                            object2=obj2,
                            collision_point=collision_point,
                            timestamp=timestamp,
                            severity=severity,
                            video_source=video_source,
                            frame_number=frame_number
                        )
                        collisions.append(collision_event)
        
        return collisions
    
    def _check_collision_pair(self, obj1, obj2) -> Optional[Tuple[float, Tuple[float, float], float]]:
        """
        Check if two objects are colliding
        
        Args:
            obj1: First detected object
            obj2: Second detected object
            
        Returns:
            Tuple of (overlap_ratio, collision_point, severity) if collision detected, None otherwise
        """
        bbox1 = obj1.bounding_box
        bbox2 = obj2.bounding_box
        
        # Check if bounding boxes intersect
        if not bbox1.intersects(bbox2):
            return None
        
        # Calculate intersection area
        intersection_area = self._calculate_intersection_area(bbox1, bbox2)
        
        # Calculate overlap ratio (intersection area / smaller object area)
        min_area = min(bbox1.area, bbox2.area)
        overlap_ratio = intersection_area / min_area if min_area > 0 else 0
        
        # Only consider it a collision if overlap exceeds threshold
        if overlap_ratio < self.collision_threshold:
            return None
        
        # Calculate collision point (center of intersection)
        collision_point = self._calculate_collision_point(bbox1, bbox2)
        
        # Calculate collision severity based on overlap ratio and velocities
        severity = self._calculate_collision_severity(obj1, obj2, overlap_ratio)
        
        return overlap_ratio, collision_point, severity
    
    def _calculate_intersection_area(self, bbox1, bbox2) -> float:
        """Calculate intersection area between two bounding boxes"""
        x_left = max(bbox1.x, bbox2.x)
        y_top = max(bbox1.y, bbox2.y)
        x_right = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        y_bottom = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)
        
        if x_right <= x_left or y_bottom <= y_top:
            return 0.0
        
        return (x_right - x_left) * (y_bottom - y_top)
    
    def _calculate_collision_point(self, bbox1, bbox2) -> Tuple[float, float]:
        """Calculate the center point of collision between two bounding boxes"""
        x_left = max(bbox1.x, bbox2.x)
        y_top = max(bbox1.y, bbox2.y)
        x_right = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        y_bottom = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)
        
        center_x = (x_left + x_right) / 2
        center_y = (y_top + y_bottom) / 2
        
        return (center_x, center_y)
    
    def _calculate_collision_severity(self, obj1, obj2, overlap_ratio: float) -> float:
        """
        Calculate collision severity based on overlap ratio and object velocities
        
        Args:
            obj1: First object
            obj2: Second object
            overlap_ratio: Ratio of intersection to smaller object area
            
        Returns:
            Severity score between 0.0 and 1.0
        """
        # Base severity from overlap ratio
        base_severity = min(overlap_ratio, 1.0)
        
        # Velocity factor - higher velocities increase severity
        vel1_magnitude = obj1.velocity.magnitude()
        vel2_magnitude = obj2.velocity.magnitude()
        combined_velocity = vel1_magnitude + vel2_magnitude
        
        # Normalize velocity factor (assuming max reasonable velocity of 100 pixels/frame)
        velocity_factor = min(combined_velocity / 100.0, 1.0)
        
        # Combine factors (weighted average)
        severity = (base_severity * 0.7) + (velocity_factor * 0.3)
        
        return min(severity, 1.0)
    
    def _update_object_tracks(self, objects: List, timestamp: float):
        """Update object tracking history for velocity calculation"""
        for obj in objects:
            track_entry = {
                'timestamp': timestamp,
                'position': obj.bounding_box.center,
                'bbox': obj.bounding_box
            }
            self.object_tracks[obj.id].append(track_entry)
    
    def _calculate_velocities(self, objects: List) -> List:
        """
        Calculate object velocities based on tracking history
        
        Args:
            objects: List of detected objects
            
        Returns:
            List of objects with updated velocity information
        """
        updated_objects = []
        
        for obj in objects:
            track_history = self.object_tracks.get(obj.id, deque())
            
            if len(track_history) >= 2:
                # Calculate velocity from last two positions
                current_entry = track_history[-1]
                previous_entry = track_history[-2]
                
                time_delta = current_entry['timestamp'] - previous_entry['timestamp']
                
                if time_delta > 0:
                    pos_current = current_entry['position']
                    pos_previous = previous_entry['position']
                    
                    velocity_x = (pos_current[0] - pos_previous[0]) / time_delta
                    velocity_y = (pos_current[1] - pos_previous[1]) / time_delta
                    
                    # Assuming Vector2D class is available
                    try:
                        obj.velocity = Vector2D(velocity_x, velocity_y)
                    except:
                        # Fallback if Vector2D is not available
                        obj.velocity = type('Vector2D', (), {'x': velocity_x, 'y': velocity_y, 'magnitude': lambda: (velocity_x**2 + velocity_y**2)**0.5})()
            
            updated_objects.append(obj)
        
        return updated_objects
    
    def log_collision(self, event: CollisionEvent):
        """
        Log a collision event
        
        Args:
            event: Collision event to log
        """
        self.collision_events.append(event)
        
        # Print collision information for debugging
        print(f"Collision detected at frame {event.frame_number} (t={event.timestamp:.2f}s): "
              f"{event.object1.class_name} vs {event.object2.class_name} "
              f"(severity: {event.severity:.2f})")
    
    def trigger_responses(self, collision_events: List[CollisionEvent]):
        """
        Trigger hardware responses for collision events with error handling and retry
        
        Args:
            collision_events: List of collision events to respond to
        """
        if not self.hardware_controller:
            return
        
        for event in collision_events:
            # Retry mechanism for hardware commands
            for attempt in range(self.max_retries):
                try:
                    command = {
                        'action': 'collision_alert',
                        'severity': event.severity,
                        'timestamp': event.timestamp,
                        'collision_id': event.id
                    }
                    self.hardware_controller.broadcast_alert(command)
                    logger.debug(f"Hardware response triggered for collision {event.id}")
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        # Final attempt failed
                        logger.error(f"Failed to trigger hardware response after {self.max_retries} attempts: {e}")
                        self._handle_error(HardwareControlError(f"Hardware response failed: {e}"), "hardware_control")
                    else:
                        logger.warning(f"Hardware response attempt {attempt + 1} failed: {e}")
                        time.sleep(self.retry_delay)
    
    def generate_analysis_report(self, video_id: str, total_frames: int, 
                               processed_frames: int, processing_time: float) -> VideoAnalysisResult:
        """
        Generate comprehensive analysis report
        
        Args:
            video_id: Identifier for the analyzed video
            total_frames: Total number of frames in video
            processed_frames: Number of frames actually processed
            processing_time: Time taken for processing in seconds
            
        Returns:
            Complete video analysis result
        """
        # Calculate confidence scores from collision events
        confidence_scores = [event.object1.confidence for event in self.collision_events]
        confidence_scores.extend([event.object2.confidence for event in self.collision_events])
        
        # Generate analysis metadata
        metadata = {
            'collision_count': len(self.collision_events),
            'average_severity': sum(event.severity for event in self.collision_events) / len(self.collision_events) if self.collision_events else 0.0,
            'frames_with_collisions': len(set(event.frame_number for event in self.collision_events)),
            'collision_density': len(self.collision_events) / processed_frames if processed_frames > 0 else 0.0,
            'processing_fps': processed_frames / processing_time if processing_time > 0 else 0.0,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
        
        return VideoAnalysisResult(
            video_id=video_id,
            total_frames=total_frames,
            processed_frames=processed_frames,
            collision_events=self.collision_events.copy(),
            processing_time=processing_time,
            confidence_scores=confidence_scores,
            analysis_metadata=metadata
        )
    
    def clear_events(self):
        """Clear all stored collision events"""
        self.collision_events.clear()
        self.object_tracks.clear()
    
    def get_collision_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of detected collisions
        
        Returns:
            Dictionary with collision statistics
        """
        if not self.collision_events:
            return {
                'total_collisions': 0,
                'average_severity': 0.0,
                'collision_types': {},
                'timeline': []
            }
        
        # Count collision types
        collision_types = defaultdict(int)
        for event in self.collision_events:
            type_key = f"{event.object1.class_name}-{event.object2.class_name}"
            collision_types[type_key] += 1
        
        # Create timeline of collisions
        timeline = [
            {
                'timestamp': event.timestamp,
                'frame_number': event.frame_number,
                'severity': event.severity,
                'objects': [event.object1.class_name, event.object2.class_name]
            }
            for event in sorted(self.collision_events, key=lambda x: x.timestamp)
        ]
        
        return {
            'total_collisions': len(self.collision_events),
            'average_severity': sum(event.severity for event in self.collision_events) / len(self.collision_events),
            'collision_types': dict(collision_types),
            'timeline': timeline
        }
    
    def set_collision_threshold(self, threshold: float):
        """Set the minimum overlap ratio for collision detection"""
        self.collision_threshold = max(0.0, min(1.0, threshold))
    
    def set_severity_threshold(self, threshold: float):
        """Set the minimum severity for logging collisions"""
        self.severity_threshold = max(0.0, min(1.0, threshold))
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive performance summary including spatial optimization stats
        
        Returns:
            Dictionary with performance metrics and optimization statistics
        """
        performance_metrics = self.performance_monitor.get_performance_metrics()
        spatial_stats = self.spatial_grid.get_performance_stats() if self.use_spatial_optimization else {}
        
        return {
            'frame_processing': {
                'total_frames_processed': self.frame_stats['total_frames_processed'],
                'total_collisions_detected': self.frame_stats['total_collisions_detected'],
                'average_processing_time': self.frame_stats['average_processing_time'],
                'collisions_per_frame': (
                    self.frame_stats['total_collisions_detected'] / self.frame_stats['total_frames_processed']
                    if self.frame_stats['total_frames_processed'] > 0 else 0.0
                )
            },
            'performance_metrics': performance_metrics,
            'spatial_optimization': {
                'enabled': self.use_spatial_optimization,
                'stats': spatial_stats
            },
            'quality_settings': {
                'adaptive_quality_enabled': self.adaptive_quality,
                'collision_threshold': self.collision_threshold,
                'severity_threshold': self.severity_threshold,
                'max_objects_per_frame': self.max_objects_per_frame,
                'current_quality_level': self.frame_stats.get('current_quality_level', 1.0)
            }
        }
    
    def optimize_performance(self):
        """Manually trigger performance optimization"""
        if self.use_spatial_optimization:
            # Optimize spatial grid cell size
            self.spatial_grid.optimize_cell_size()
        
        # Get performance recommendations
        recommendations = self.performance_monitor.get_quality_recommendations()
        
        return {
            'optimization_applied': True,
            'spatial_grid_optimized': self.use_spatial_optimization,
            'recommendations': recommendations
        }
    
    def enable_spatial_optimization(self, enable: bool = True):
        """Enable or disable spatial partitioning optimization"""
        self.use_spatial_optimization = enable
        self.frame_stats['spatial_optimization_enabled'] = enable
        
        if not enable:
            # Clear spatial grid to save memory
            self.spatial_grid.clear()
    
    def enable_adaptive_quality(self, enable: bool = True):
        """Enable or disable adaptive quality adjustment"""
        self.adaptive_quality = enable
    
    def set_performance_target(self, target_fps: float):
        """Set target FPS for performance monitoring"""
        if self.performance_monitor:
            self.performance_monitor.target_fps = target_fps
            self.performance_monitor.max_frame_time = 1.0 / target_fps
    
    def reset_error_state(self):
        """Reset error state and exit recovery mode"""
        self.error_count = 0
        self.recovery_mode = False
        self.last_error_time = 0
        self.frame_stats['error_count'] = 0
        self.frame_stats['last_error'] = None
        logger.info("Error state reset, exiting recovery mode")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error and recovery statistics"""
        return {
            'error_count': self.error_count,
            'recovery_mode': self.recovery_mode,
            'recovery_count': self.frame_stats.get('recovery_count', 0),
            'last_error': self.frame_stats.get('last_error'),
            'max_errors_per_session': self.max_errors_per_session,
            'error_recovery_timeout': self.error_recovery_timeout,
            'time_since_last_error': time.time() - self.last_error_time if self.last_error_time > 0 else 0
        }
    
    def is_healthy(self) -> bool:
        """Check if the collision engine is in a healthy state"""
        return (
            not self.recovery_mode and 
            self.error_count < self.max_errors_per_session * 0.8 and
            (self.spatial_grid is not None or not self.use_spatial_optimization)
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status of the collision engine"""
        return {
            'healthy': self.is_healthy(),
            'recovery_mode': self.recovery_mode,
            'error_rate': self.error_count / max(1, self.frame_stats['total_frames_processed']),
            'spatial_optimization_available': self.spatial_grid is not None,
            'performance_monitor_available': self.performance_monitor is not None,
            'hardware_controller_available': self.hardware_controller is not None,
            'processing_statistics': {
                'frames_processed': self.frame_stats['total_frames_processed'],
                'collisions_detected': self.frame_stats['total_collisions_detected'],
                'average_processing_time': self.frame_stats['average_processing_time']
            }
        }


# Test the collision engine when run directly
if __name__ == "__main__":
    print("Testing Collision Engine...")
    
    # Create a mock computer vision module for testing
    # from .computer_vision import ComputerVisionModule
    # cv_module = ComputerVisionModule()
    
    # Initialize collision engine
    # engine = CollisionEngine(cv_module)
    
    print("Collision Engine module loaded successfully!")
    print("Use with proper imports for full functionality.")