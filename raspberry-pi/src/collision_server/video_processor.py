"""
Video processing infrastructure for collision detection
"""
import os
import cv2
import threading
import time
import base64
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from .utils import validate_video_format, get_file_size, format_file_size
from .resource_manager import ProcessingTask, TaskPriority
# from .computer_vision import ComputerVisionModule
# from .collision_engine import CollisionEngine


class ProcessingStatus(Enum):
    """Video processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CameraStatus(Enum):
    """Camera feed status enumeration"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class CameraFeed:
    """Camera feed information"""
    camera_id: int
    status: CameraStatus
    fps: float
    width: int
    height: int
    start_time: Optional[datetime]
    frame_count: int
    error_message: Optional[str]


@dataclass
class VideoMetadata:
    """Video file metadata"""
    filename: str
    file_path: str
    file_size: int
    duration: float
    fps: float
    frame_count: int
    width: int
    height: int
    format: str


@dataclass
class ProcessingJob:
    """Video processing job information"""
    job_id: str
    video_metadata: VideoMetadata
    status: ProcessingStatus
    progress: float
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error_message: Optional[str]
    results: Optional[Dict[str, Any]]


class VideoProcessor:
    """Video processing class with file handling and format support"""
    
    def __init__(self, upload_folder: str, progress_callback: Optional[Callable] = None, 
                 enable_collision_detection: bool = True, frame_callback: Optional[Callable] = None,
                 resource_manager=None):
        """
        Initialize VideoProcessor
        
        Args:
            upload_folder: Directory containing uploaded video files
            progress_callback: Optional callback for progress updates
            enable_collision_detection: Whether to enable collision detection during processing
            frame_callback: Optional callback for real-time frame streaming
            resource_manager: Resource manager for task prioritization
        """
        self.upload_folder = upload_folder
        self.progress_callback = progress_callback
        self.frame_callback = frame_callback
        self.resource_manager = resource_manager
        self.processing_jobs: Dict[str, ProcessingJob] = {}
        self.active_threads: Dict[str, threading.Thread] = {}
        self._stop_flags: Dict[str, threading.Event] = {}
        
        # Camera feed management
        self.camera_feeds: Dict[int, CameraFeed] = {}
        self.camera_threads: Dict[int, threading.Thread] = {}
        self.camera_stop_flags: Dict[int, threading.Event] = {}
        self.camera_captures: Dict[int, cv2.VideoCapture] = {}
        
        # Initialize collision detection components if enabled
        self.enable_collision_detection = enable_collision_detection
        if enable_collision_detection:
            # self.cv_module = ComputerVisionModule()
            # self.collision_engine = CollisionEngine(self.cv_module)
            self.cv_module = None
            self.collision_engine = None
            print("Collision detection temporarily disabled - computer vision module not available")
        else:
            self.cv_module = None
            self.collision_engine = None
    
    def validate_video_file(self, file_path: str) -> bool:
        """
        Validate video file format and accessibility
        
        Args:
            file_path: Path to video file
            
        Returns:
            True if file is valid, False otherwise
        """
        if not os.path.exists(file_path):
            return False
        
        if not validate_video_format(file_path):
            return False
        
        # Try to open with OpenCV to verify it's a valid video
        try:
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return False
            
            # Check if we can read at least one frame
            ret, frame = cap.read()
            cap.release()
            return ret and frame is not None
        except Exception:
            return False
    
    def get_video_metadata(self, file_path: str) -> Optional[VideoMetadata]:
        """
        Extract metadata from video file
        
        Args:
            file_path: Path to video file
            
        Returns:
            VideoMetadata object or None if extraction fails
        """
        if not self.validate_video_file(file_path):
            return None
        
        try:
            cap = cv2.VideoCapture(file_path)
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate duration
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            # Get file information
            file_size = get_file_size(file_path)
            filename = os.path.basename(file_path)
            file_format = os.path.splitext(filename)[1].lower()
            
            return VideoMetadata(
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                duration=duration,
                fps=fps,
                frame_count=frame_count,
                width=width,
                height=height,
                format=file_format
            )
        except Exception as e:
            print(f"Error extracting video metadata: {e}")
            return None
    
    def create_processing_job(self, job_id: str, file_path: str) -> Optional[ProcessingJob]:
        """
        Create a new video processing job
        
        Args:
            job_id: Unique identifier for the job
            file_path: Path to video file
            
        Returns:
            ProcessingJob object or None if creation fails
        """
        metadata = self.get_video_metadata(file_path)
        if not metadata:
            return None
        
        job = ProcessingJob(
            job_id=job_id,
            video_metadata=metadata,
            status=ProcessingStatus.PENDING,
            progress=0.0,
            start_time=None,
            end_time=None,
            error_message=None,
            results=None
        )
        
        self.processing_jobs[job_id] = job
        return job
    
    def start_processing(self, job_id: str) -> bool:
        """
        Start processing a video file using resource manager if available
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if processing started successfully, False otherwise
        """
        if job_id not in self.processing_jobs:
            return False
        
        job = self.processing_jobs[job_id]
        if job.status != ProcessingStatus.PENDING:
            return False
        
        # Use resource manager if available
        if self.resource_manager:
            # Create processing task for resource manager
            task = ProcessingTask(
                task_id=f"video_processing_{job_id}",
                task_type="video_processing",
                priority=TaskPriority.NORMAL,  # Video processing has normal priority
                callback=self._process_video_managed,
                args=(job_id,),
                kwargs={},
                estimated_cpu_usage=40.0,  # Video processing is CPU intensive
                estimated_memory_mb=200.0,  # Estimate based on video size
                estimated_duration=job.video_metadata.duration * 2  # Rough estimate
            )
            
            # Submit task to resource manager
            if self.resource_manager.submit_task(task):
                job.status = ProcessingStatus.PROCESSING
                return True
            else:
                return False
        else:
            # Fallback to direct processing
            # Create stop flag for this job
            self._stop_flags[job_id] = threading.Event()
            
            # Start processing in separate thread
            thread = threading.Thread(
                target=self._process_video_thread,
                args=(job_id,),
                daemon=True
            )
            
            self.active_threads[job_id] = thread
            thread.start()
            
            return True
    
    def stop_processing(self, job_id: str) -> bool:
        """
        Stop processing a video file
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if stop signal sent successfully, False otherwise
        """
        if job_id not in self._stop_flags:
            return False
        
        self._stop_flags[job_id].set()
        
        if job_id in self.processing_jobs:
            self.processing_jobs[job_id].status = ProcessingStatus.CANCELLED
        
        return True
    
    def get_processing_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get processing status for a job
        
        Args:
            job_id: Job identifier
            
        Returns:
            Status dictionary or None if job not found
        """
        if job_id not in self.processing_jobs:
            return None
        
        job = self.processing_jobs[job_id]
        return {
            'job_id': job_id,
            'status': job.status.value,
            'progress': job.progress,
            'start_time': job.start_time.isoformat() if job.start_time else None,
            'end_time': job.end_time.isoformat() if job.end_time else None,
            'error_message': job.error_message,
            'video_metadata': asdict(job.video_metadata),
            'results': job.results
        }
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Get status of all processing jobs
        
        Returns:
            List of job status dictionaries
        """
        return [self.get_processing_status(job_id) for job_id in self.processing_jobs.keys()]
    
    def _process_video_thread(self, job_id: str) -> None:
        """
        Process video in separate thread
        
        Args:
            job_id: Job identifier
        """
        job = self.processing_jobs[job_id]
        stop_flag = self._stop_flags[job_id]
        
        try:
            # Update job status
            job.status = ProcessingStatus.PROCESSING
            job.start_time = datetime.utcnow()
            job.progress = 0.0
            
            # Clear previous collision events if collision detection is enabled
            if self.collision_engine:
                self.collision_engine.clear_events()
            
            # Notify progress callback
            if self.progress_callback:
                self.progress_callback(job_id, 0.0, ProcessingStatus.PROCESSING.value)
            
            # Open video file
            cap = cv2.VideoCapture(job.video_metadata.file_path)
            if not cap.isOpened():
                raise Exception("Failed to open video file")
            
            frame_count = job.video_metadata.frame_count
            fps = job.video_metadata.fps
            processed_frames = 0
            collision_events = []
            
            # Process frames
            while True:
                if stop_flag.is_set():
                    job.status = ProcessingStatus.CANCELLED
                    break
                
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Calculate timestamp for this frame
                timestamp = processed_frames / fps if fps > 0 else processed_frames * 0.033
                
                # Perform collision detection if enabled
                if self.collision_engine and frame is not None:
                    try:
                        frame_collisions = self.collision_engine.analyze_frame(
                            frame, timestamp, processed_frames, job.video_metadata.filename
                        )
                        collision_events.extend(frame_collisions)
                    except Exception as e:
                        print(f"Collision detection error at frame {processed_frames}: {e}")
                
                processed_frames += 1
                progress = (processed_frames / frame_count) * 100.0
                job.progress = progress
                
                # Update progress every 10 frames
                if processed_frames % 10 == 0 and self.progress_callback:
                    self.progress_callback(job_id, progress, ProcessingStatus.PROCESSING.value)
            
            cap.release()
            
            # Complete processing if not cancelled
            if job.status == ProcessingStatus.PROCESSING:
                job.status = ProcessingStatus.COMPLETED
                job.progress = 100.0
                
                # Generate collision detection results
                collision_results = {}
                if self.collision_engine:
                    analysis_result = self.collision_engine.generate_analysis_report(
                        job_id, frame_count, processed_frames, 
                        (datetime.utcnow() - job.start_time).total_seconds()
                    )
                    collision_results = {
                        'collision_events': [asdict(event) for event in analysis_result.collision_events],
                        'collision_summary': self.collision_engine.get_collision_summary(),
                        'analysis_metadata': analysis_result.analysis_metadata
                    }
                
                job.results = {
                    'processed_frames': processed_frames,
                    'total_frames': frame_count,
                    'processing_time': (datetime.utcnow() - job.start_time).total_seconds(),
                    **collision_results
                }
                
                if self.progress_callback:
                    self.progress_callback(job_id, 100.0, ProcessingStatus.COMPLETED.value)
            
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            
            if self.progress_callback:
                self.progress_callback(job_id, job.progress, ProcessingStatus.FAILED.value)
        
        finally:
            job.end_time = datetime.utcnow()
            
            # Clean up
            if job_id in self.active_threads:
                del self.active_threads[job_id]
            if job_id in self._stop_flags:
                del self._stop_flags[job_id]
    
    def cleanup_completed_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed jobs
        
        Args:
            max_age_hours: Maximum age of completed jobs to keep
            
        Returns:
            Number of jobs cleaned up
        """
        current_time = datetime.utcnow()
        jobs_to_remove = []
        
        for job_id, job in self.processing_jobs.items():
            if job.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
                if job.end_time:
                    age_hours = (current_time - job.end_time).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.processing_jobs[job_id]
        
        return len(jobs_to_remove)
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported video formats
        
        Returns:
            List of supported file extensions
        """
        return ['.mp4', '.avi', '.mov', '.webm']
    
    def get_collision_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get collision detection results for a completed job
        
        Args:
            job_id: Job identifier
            
        Returns:
            Collision detection results or None if job not found or not completed
        """
        if job_id not in self.processing_jobs:
            return None
        
        job = self.processing_jobs[job_id]
        if job.status != ProcessingStatus.COMPLETED or not job.results:
            return None
        
        # Extract collision-related results
        return {
            'collision_events': job.results.get('collision_events', []),
            'collision_summary': job.results.get('collision_summary', {}),
            'analysis_metadata': job.results.get('analysis_metadata', {}),
            'processing_time': job.results.get('processing_time', 0.0),
            'processed_frames': job.results.get('processed_frames', 0),
            'total_frames': job.results.get('total_frames', 0)
        }
    
    def set_collision_thresholds(self, collision_threshold: float = None, severity_threshold: float = None):
        """
        Set collision detection thresholds
        
        Args:
            collision_threshold: Minimum overlap ratio for collision detection
            severity_threshold: Minimum severity for logging collisions
        """
        if self.collision_engine:
            if collision_threshold is not None:
                self.collision_engine.set_collision_threshold(collision_threshold)
            if severity_threshold is not None:
                self.collision_engine.set_severity_threshold(severity_threshold)
    
    def _process_video_managed(self, job_id: str) -> None:
        """
        Process video through resource manager (wrapper for _process_video_thread)
        
        Args:
            job_id: Job identifier
        """
        # Create stop flag for this job if not exists
        if job_id not in self._stop_flags:
            self._stop_flags[job_id] = threading.Event()
        
        # Call the actual processing method
        self._process_video_thread(job_id)
    
    def start_camera_feed(self, camera_id: int = 0) -> bool:
        """
        Start real-time camera feed processing with resource management
        
        Args:
            camera_id: Camera device ID (default: 0 for primary camera)
            
        Returns:
            True if camera feed started successfully, False otherwise
        """
        if camera_id in self.camera_feeds and self.camera_feeds[camera_id].status == CameraStatus.RUNNING:
            return False  # Camera already running
        
        try:
            # Test camera access
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                return False
            
            # Get camera properties
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0  # Default to 30 FPS if not available
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Test frame capture
            ret, frame = cap.read()
            if not ret or frame is None:
                cap.release()
                return False
            
            cap.release()
            
            # Create camera feed info
            camera_feed = CameraFeed(
                camera_id=camera_id,
                status=CameraStatus.STARTING,
                fps=fps,
                width=width,
                height=height,
                start_time=datetime.utcnow(),
                frame_count=0,
                error_message=None
            )
            
            self.camera_feeds[camera_id] = camera_feed
            
            # Use resource manager for real-time camera processing if available
            if self.resource_manager:
                # Create real-time processing task
                task = ProcessingTask(
                    task_id=f"camera_feed_{camera_id}",
                    task_type="real_time_camera",
                    priority=TaskPriority.REAL_TIME,  # Highest priority for real-time
                    callback=self._camera_feed_managed,
                    args=(camera_id,),
                    kwargs={},
                    estimated_cpu_usage=20.0,  # Real-time processing should be lighter
                    estimated_memory_mb=50.0,
                    estimated_duration=float('inf')  # Continuous processing
                )
                
                # Submit task to resource manager
                if self.resource_manager.submit_task(task):
                    return True
                else:
                    # Fallback to direct processing if resource manager rejects
                    pass
            
            # Fallback to direct camera processing
            # Create stop flag for this camera
            self.camera_stop_flags[camera_id] = threading.Event()
            
            # Start camera processing in separate thread
            thread = threading.Thread(
                target=self._camera_feed_thread,
                args=(camera_id,),
                daemon=True
            )
            
            self.camera_threads[camera_id] = thread
            thread.start()
            
            return True
            
        except Exception as e:
            print(f"Error starting camera feed {camera_id}: {e}")
            return False
    
    def _camera_feed_managed(self, camera_id: int) -> None:
        """
        Process camera feed through resource manager (wrapper for _camera_feed_thread)
        
        Args:
            camera_id: Camera device ID
        """
        # Create stop flag for this camera if not exists
        if camera_id not in self.camera_stop_flags:
            self.camera_stop_flags[camera_id] = threading.Event()
        
        # Call the actual camera processing method
        self._camera_feed_thread(camera_id)
    
    def stop_camera_feed(self, camera_id: int) -> bool:
        """
        Stop real-time camera feed processing
        
        Args:
            camera_id: Camera device ID
            
        Returns:
            True if camera feed stopped successfully, False otherwise
        """
        if camera_id not in self.camera_stop_flags:
            return False
        
        # Signal stop
        self.camera_stop_flags[camera_id].set()
        
        # Update status
        if camera_id in self.camera_feeds:
            self.camera_feeds[camera_id].status = CameraStatus.STOPPED
        
        # Wait for thread to finish (with timeout)
        if camera_id in self.camera_threads:
            self.camera_threads[camera_id].join(timeout=5.0)
        
        return True
    
    def get_camera_status(self, camera_id: int) -> Optional[Dict[str, Any]]:
        """
        Get status of a camera feed
        
        Args:
            camera_id: Camera device ID
            
        Returns:
            Camera status dictionary or None if camera not found
        """
        if camera_id not in self.camera_feeds:
            return None
        
        feed = self.camera_feeds[camera_id]
        return {
            'camera_id': feed.camera_id,
            'status': feed.status.value,
            'fps': feed.fps,
            'width': feed.width,
            'height': feed.height,
            'start_time': feed.start_time.isoformat() if feed.start_time else None,
            'frame_count': feed.frame_count,
            'error_message': feed.error_message,
            'uptime': (datetime.utcnow() - feed.start_time).total_seconds() if feed.start_time else 0
        }
    
    def get_all_camera_feeds(self) -> List[Dict[str, Any]]:
        """
        Get status of all camera feeds
        
        Returns:
            List of camera status dictionaries
        """
        return [self.get_camera_status(camera_id) for camera_id in self.camera_feeds.keys()]
    
    def _camera_feed_thread(self, camera_id: int) -> None:
        """
        Process camera feed in separate thread
        
        Args:
            camera_id: Camera device ID
        """
        feed = self.camera_feeds[camera_id]
        stop_flag = self.camera_stop_flags[camera_id]
        
        try:
            # Open camera
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                raise Exception(f"Failed to open camera {camera_id}")
            
            self.camera_captures[camera_id] = cap
            feed.status = CameraStatus.RUNNING
            
            # Set camera properties for better performance
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize latency
            
            frame_interval = 1.0 / feed.fps
            last_frame_time = time.time()
            
            while not stop_flag.is_set():
                current_time = time.time()
                
                # Maintain frame rate
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.001)  # Small sleep to prevent busy waiting
                    continue
                
                ret, frame = cap.read()
                if not ret or frame is None:
                    print(f"Failed to read frame from camera {camera_id}")
                    time.sleep(0.1)
                    continue
                
                feed.frame_count += 1
                last_frame_time = current_time
                
                # Process frame for collision detection if enabled
                if self.collision_engine and frame is not None:
                    try:
                        timestamp = current_time
                        frame_collisions = self.collision_engine.analyze_frame(
                            frame, timestamp, feed.frame_count, f"camera_{camera_id}"
                        )
                        
                        # If collisions detected, trigger alerts
                        if frame_collisions:
                            self._handle_camera_collisions(camera_id, frame_collisions, frame)
                    except Exception as e:
                        print(f"Collision detection error for camera {camera_id}: {e}")
                
                # Stream frame to web interface if callback provided
                if self.frame_callback:
                    try:
                        # Encode frame as JPEG for streaming
                        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        frame_data = base64.b64encode(buffer).decode('utf-8')
                        
                        self.frame_callback(camera_id, frame_data, {
                            'timestamp': current_time,
                            'frame_count': feed.frame_count,
                            'width': feed.width,
                            'height': feed.height
                        })
                    except Exception as e:
                        print(f"Frame streaming error for camera {camera_id}: {e}")
                
        except Exception as e:
            feed.status = CameraStatus.ERROR
            feed.error_message = str(e)
            print(f"Camera feed error for camera {camera_id}: {e}")
        
        finally:
            # Cleanup
            if camera_id in self.camera_captures:
                self.camera_captures[camera_id].release()
                del self.camera_captures[camera_id]
            
            if camera_id in self.camera_threads:
                del self.camera_threads[camera_id]
            
            if camera_id in self.camera_stop_flags:
                del self.camera_stop_flags[camera_id]
            
            feed.status = CameraStatus.STOPPED
    
    def _handle_camera_collisions(self, camera_id: int, collisions: List[Any], frame: np.ndarray) -> None:
        """
        Handle collision events detected in camera feed
        
        Args:
            camera_id: Camera device ID
            collisions: List of collision events
            frame: Current video frame
        """
        for collision in collisions:
            print(f"Real-time collision detected on camera {camera_id}: {collision}")
            
            # Trigger immediate alert system
            self._trigger_collision_alert(camera_id, collision, frame)
    
    def _trigger_collision_alert(self, camera_id: int, collision: Any, frame: np.ndarray) -> None:
        """
        Trigger immediate alert system for live collisions
        
        Args:
            camera_id: Camera device ID
            collision: Collision event data
            frame: Current video frame
        """
        try:
            # Create alert data
            alert_data = {
                'camera_id': camera_id,
                'collision_id': getattr(collision, 'id', f"camera_{camera_id}_{int(time.time())}"),
                'timestamp': datetime.utcnow().isoformat(),
                'severity': getattr(collision, 'severity', 1.0),
                'objects': getattr(collision, 'objects', []),
                'collision_point': {
                    'x': getattr(collision.collision_point, 'x', 0) if hasattr(collision, 'collision_point') else 0,
                    'y': getattr(collision.collision_point, 'y', 0) if hasattr(collision, 'collision_point') else 0
                } if hasattr(collision, 'collision_point') else {'x': 0, 'y': 0}
            }
            
            # Emit real-time alert via WebSocket if callback available
            if self.frame_callback:
                # Include collision overlay in frame data
                frame_with_overlay = self._add_collision_overlay(frame, collision)
                _, buffer = cv2.imencode('.jpg', frame_with_overlay, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_data = base64.b64encode(buffer).decode('utf-8')
                
                # Get camera feed info if available, otherwise use defaults
                camera_feed = self.camera_feeds.get(camera_id)
                if camera_feed:
                    width = camera_feed.width
                    height = camera_feed.height
                    frame_count = camera_feed.frame_count
                else:
                    # Use frame dimensions if camera feed not available
                    height, width = frame.shape[:2] if frame is not None else (480, 640)
                    frame_count = 1
                
                # Send frame with collision data
                self.frame_callback(camera_id, frame_data, {
                    'timestamp': time.time(),
                    'frame_count': frame_count,
                    'width': width,
                    'height': height,
                    'detections': [alert_data],
                    'alert': True
                })
            
            # Log the collision alert
            print(f"COLLISION ALERT - Camera {camera_id}: {alert_data}")
            
            # Store alert for retrieval
            if not hasattr(self, 'collision_alerts'):
                self.collision_alerts = {}
            if camera_id not in self.collision_alerts:
                self.collision_alerts[camera_id] = []
            
            self.collision_alerts[camera_id].append(alert_data)
            
            # Keep only last 100 alerts per camera
            if len(self.collision_alerts[camera_id]) > 100:
                self.collision_alerts[camera_id] = self.collision_alerts[camera_id][-100:]
                
        except Exception as e:
            print(f"Error triggering collision alert for camera {camera_id}: {e}")
    
    def _add_collision_overlay(self, frame: np.ndarray, collision: Any) -> np.ndarray:
        """
        Add visual collision overlay to frame
        
        Args:
            frame: Original video frame
            collision: Collision event data
            
        Returns:
            Frame with collision overlay
        """
        try:
            overlay_frame = frame.copy()
            
            # Draw collision indicator (red circle at collision point)
            if hasattr(collision, 'collision_point'):
                center = (
                    int(getattr(collision.collision_point, 'x', frame.shape[1] // 2)),
                    int(getattr(collision.collision_point, 'y', frame.shape[0] // 2))
                )
                cv2.circle(overlay_frame, center, 30, (0, 0, 255), 3)  # Red circle
                cv2.putText(overlay_frame, "COLLISION", (center[0] - 50, center[1] - 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Draw bounding boxes for colliding objects
            if hasattr(collision, 'object1') and hasattr(collision.object1, 'bounding_box'):
                bbox = collision.object1.bounding_box
                if hasattr(bbox, 'x') and hasattr(bbox, 'y') and hasattr(bbox, 'width') and hasattr(bbox, 'height'):
                    x, y, w, h = int(bbox.x), int(bbox.y), int(bbox.width), int(bbox.height)
                    cv2.rectangle(overlay_frame, (x, y), (x + w, y + h), (0, 255, 255), 2)  # Yellow box
            
            if hasattr(collision, 'object2') and hasattr(collision.object2, 'bounding_box'):
                bbox = collision.object2.bounding_box
                if hasattr(bbox, 'x') and hasattr(bbox, 'y') and hasattr(bbox, 'width') and hasattr(bbox, 'height'):
                    x, y, w, h = int(bbox.x), int(bbox.y), int(bbox.width), int(bbox.height)
                    cv2.rectangle(overlay_frame, (x, y), (x + w, y + h), (255, 0, 255), 2)  # Magenta box
            
            # Add timestamp
            timestamp_text = f"ALERT: {datetime.utcnow().strftime('%H:%M:%S')}"
            cv2.putText(overlay_frame, timestamp_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            return overlay_frame
            
        except Exception as e:
            print(f"Error adding collision overlay: {e}")
            return frame
    
    def get_collision_alerts(self, camera_id: int = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get collision alerts for camera(s)
        
        Args:
            camera_id: Specific camera ID, or None for all cameras
            limit: Maximum number of alerts to return
            
        Returns:
            List of collision alert dictionaries
        """
        if not hasattr(self, 'collision_alerts'):
            return []
        
        if camera_id is not None:
            alerts = self.collision_alerts.get(camera_id, [])
            return alerts[-limit:] if limit else alerts
        else:
            # Return alerts from all cameras
            all_alerts = []
            for cam_id, alerts in self.collision_alerts.items():
                for alert in alerts:
                    all_alerts.append(alert)
            
            # Sort by timestamp and return most recent
            all_alerts.sort(key=lambda x: x['timestamp'], reverse=True)
            return all_alerts[:limit] if limit else all_alerts
    
    def clear_collision_alerts(self, camera_id: int = None) -> bool:
        """
        Clear collision alerts for camera(s)
        
        Args:
            camera_id: Specific camera ID, or None for all cameras
            
        Returns:
            True if alerts cleared successfully
        """
        if not hasattr(self, 'collision_alerts'):
            return True
        
        try:
            if camera_id is not None:
                if camera_id in self.collision_alerts:
                    self.collision_alerts[camera_id] = []
            else:
                self.collision_alerts = {}
            return True
        except Exception:
            return False
    
    def get_available_cameras(self) -> List[int]:
        """
        Detect available camera devices
        
        Returns:
            List of available camera IDs
        """
        available_cameras = []
        
        # Test camera IDs 0-9 (common range)
        for camera_id in range(10):
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    available_cameras.append(camera_id)
            cap.release()
        
        return available_cameras
    
    def capture_frame(self, camera_id: int) -> Optional[np.ndarray]:
        """
        Capture a single frame from camera
        
        Args:
            camera_id: Camera device ID
            
        Returns:
            Frame as numpy array or None if capture fails
        """
        if camera_id in self.camera_captures:
            cap = self.camera_captures[camera_id]
            ret, frame = cap.read()
            return frame if ret else None
        
        # Try to capture from inactive camera
        try:
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                return frame if ret else None
        except Exception:
            pass
        
        return None
    
    def start_all_available_cameras(self) -> Dict[int, bool]:
        """
        Start all available camera feeds
        
        Returns:
            Dictionary mapping camera_id to success status
        """
        available_cameras = self.get_available_cameras()
        results = {}
        
        for camera_id in available_cameras:
            success = self.start_camera_feed(camera_id)
            results[camera_id] = success
            
            if success:
                print(f"Started camera {camera_id}")
            else:
                print(f"Failed to start camera {camera_id}")
        
        return results
    
    def stop_all_cameras(self) -> Dict[int, bool]:
        """
        Stop all active camera feeds
        
        Returns:
            Dictionary mapping camera_id to success status
        """
        results = {}
        active_cameras = list(self.camera_feeds.keys())
        
        for camera_id in active_cameras:
            success = self.stop_camera_feed(camera_id)
            results[camera_id] = success
        
        return results
    
    def get_camera_management_status(self) -> Dict[str, Any]:
        """
        Get comprehensive camera management status
        
        Returns:
            Status dictionary with camera information
        """
        available_cameras = self.get_available_cameras()
        active_cameras = list(self.camera_feeds.keys())
        
        camera_details = {}
        for camera_id in available_cameras:
            if camera_id in self.camera_feeds:
                camera_details[camera_id] = self.get_camera_status(camera_id)
            else:
                camera_details[camera_id] = {
                    'camera_id': camera_id,
                    'status': 'available',
                    'active': False
                }
        
        return {
            'available_cameras': available_cameras,
            'active_cameras': active_cameras,
            'total_available': len(available_cameras),
            'total_active': len(active_cameras),
            'camera_details': camera_details,
            'concurrent_processing': True
        }
    
    def switch_camera_feed(self, from_camera_id: int, to_camera_id: int) -> bool:
        """
        Switch from one camera feed to another
        
        Args:
            from_camera_id: Camera to stop
            to_camera_id: Camera to start
            
        Returns:
            True if switch was successful
        """
        try:
            # Stop the current camera
            stop_success = self.stop_camera_feed(from_camera_id)
            
            # Start the new camera
            start_success = self.start_camera_feed(to_camera_id)
            
            return stop_success and start_success
        except Exception as e:
            print(f"Error switching cameras from {from_camera_id} to {to_camera_id}: {e}")
            return False