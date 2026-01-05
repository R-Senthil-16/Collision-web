#!/usr/bin/env python3
"""
Integrated Collision Detection Server with Video Analysis
Runs collision detection on uploaded videos and shows results with bounding boxes
"""
import os
import sys
import logging
import cv2
import numpy as np
import time
import json
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

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

class VideoCollisionDetector:
    def __init__(self, model_path='yolov8n.pt', params: DetectionParams = None):
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.model_available = True
            logger.info(f"YOLO model loaded: {model_path}")
        except ImportError:
            logger.warning("YOLO not available - using simulation mode")
            self.model_available = False
        except Exception as e:
            logger.warning(f"YOLO model failed to load: {e} - using simulation mode")
            self.model_available = False
            
        self.params = params if params is not None else DetectionParams()
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, bool, List[Dict]]:
        """Process a single frame for collision detection"""
        if not self.model_available:
            return self._simulate_detection(frame)
            
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
                        'class_name': self.model.names[int(box.cls[0])]
                    })
        
        # If nothing detected, return frame
        if not vehicles:
            return frame, False, []
        
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
            label_base = v['class_name']
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
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label with background
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, self.params.text_scale, self.params.text_thickness)[0]
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), color, -1)
            
            cv2.putText(
                frame,
                label,
                (x1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                self.params.text_scale,
                (255, 255, 255),  # White text
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
        
        return frame, head_on_warning, vehicles
    
    def _simulate_detection(self, frame: np.ndarray) -> Tuple[np.ndarray, bool, List[Dict]]:
        """Simulate detection when YOLO is not available"""
        height, width = frame.shape[:2]
        
        # Create fake detections for demonstration
        vehicles = [
            {
                'box': (width//4, height//3, width//2, height//2),
                'center': (width//3, height//2.5),
                'class': 2,
                'confidence': 0.85,
                'class_name': 'car',
                'threat_score': 0.15
            }
        ]
        
        # Draw simulated detection
        for v in vehicles:
            x1, y1, x2, y2 = v['box']
            label = f"SIMULATED: {v['class_name']} {v['confidence']:.2f}"
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.params.safe_color, self.params.safe_thickness)
            cv2.putText(
                frame,
                label,
                (x1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                self.params.text_scale,
                self.params.safe_color,
                self.params.text_thickness,
            )
        
        # Add simulation notice
        cv2.putText(
            frame,
            "SIMULATION MODE - Install YOLO for real detection",
            (10, height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            1,
        )
        
        return frame, False, vehicles

def create_collision_app():
    """Create Flask app with collision detection"""
    try:
        from flask import Flask, jsonify, request, send_from_directory, render_template_string
        from flask_socketio import SocketIO
        from flask_cors import CORS
        import eventlet
    except ImportError as e:
        logger.error(f"Failed to import required dependencies: {e}")
        sys.exit(1)
    
    # Use eventlet for production
    eventlet.monkey_patch()
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'production-secret-key')
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', '/tmp/collision_uploads')
    app.config['PROCESSED_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'processed')
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
    
    # Enable CORS
    CORS(app, origins="*")
    
    # Initialize SocketIO
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*", 
        async_mode='eventlet',
        logger=False,
        engineio_logger=False
    )
    
    # Create directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
    
    # Initialize collision detector
    detector = VideoCollisionDetector()
    
    # Enhanced HTML template with collision detection
    COLLISION_HTML = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Collision Detection - Video Analysis</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px; 
                background-color: #f5f5f5;
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 30px; 
                border-radius: 15px; 
                text-align: center; 
                margin-bottom: 30px;
            }
            .upload-section, .results-section { 
                background: white; 
                padding: 30px; 
                border-radius: 15px; 
                margin-bottom: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
            .upload-area {
                border: 3px dashed #667eea;
                border-radius: 10px;
                padding: 40px;
                text-align: center;
                margin: 20px 0;
                transition: all 0.3s ease;
            }
            .upload-area:hover {
                border-color: #764ba2;
                background-color: #f8f9ff;
            }
            .upload-btn, .analyze-btn {
                background: #667eea;
                color: white;
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px;
                transition: background 0.3s ease;
            }
            .upload-btn:hover, .analyze-btn:hover {
                background: #764ba2;
            }
            .analyze-btn:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            .progress-bar {
                width: 100%;
                height: 20px;
                background-color: #e0e0e0;
                border-radius: 10px;
                overflow: hidden;
                margin: 20px 0;
                display: none;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea, #764ba2);
                width: 0%;
                transition: width 0.3s ease;
            }
            .result {
                margin-top: 20px;
                padding: 15px;
                border-radius: 8px;
                display: none;
            }
            .result.success {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .result.error {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .video-container {
                display: flex;
                gap: 20px;
                margin-top: 20px;
            }
            .video-box {
                flex: 1;
                text-align: center;
            }
            .video-box h4 {
                margin-bottom: 10px;
                color: #333;
            }
            .video-preview {
                max-width: 100%;
                border-radius: 8px;
                border: 2px solid #ddd;
            }
            .analysis-results {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
            }
            .detection-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }
            .stat-box {
                background: white;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                border: 1px solid #ddd;
            }
            .stat-number {
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                color: #666;
                font-size: 14px;
            }
            .file-input { display: none; }
            .hidden { display: none; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚗 Collision Detection System</h1>
            <p>Advanced Video Analysis with Bounding Box Visualization</p>
        </div>

        <div class="upload-section">
            <h2>📹 Upload Video for Collision Analysis</h2>
            <div class="upload-area" id="uploadArea">
                <div>
                    <h3>Drop your video file here</h3>
                    <p>or</p>
                    <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                        Choose Video File
                    </button>
                    <input type="file" id="fileInput" class="file-input" accept="video/*" onchange="handleFileSelect(event)">
                </div>
                <p style="margin-top: 20px; color: #666;">
                    Supported formats: MP4, AVI, MOV, WMV<br>
                    Maximum file size: 500MB
                </p>
            </div>
            
            <div class="progress-bar" id="progressBar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            
            <div class="result" id="result"></div>
            
            <div id="videoSection" class="hidden">
                <video id="originalVideo" class="video-preview" controls style="max-width: 100%; margin-top: 20px;"></video>
                <br>
                <button id="analyzeBtn" class="analyze-btn" onclick="analyzeVideo()" disabled>
                    🔍 Analyze for Collisions
                </button>
            </div>
        </div>

        <div id="resultsSection" class="results-section hidden">
            <h2>📊 Analysis Results</h2>
            <div class="video-container">
                <div class="video-box">
                    <h4>Original Video</h4>
                    <video id="originalResult" class="video-preview" controls></video>
                </div>
                <div class="video-box">
                    <h4>Processed Video (with Bounding Boxes)</h4>
                    <video id="processedResult" class="video-preview" controls></video>
                </div>
            </div>
            
            <div class="analysis-results">
                <h3>Detection Summary</h3>
                <div class="detection-stats" id="detectionStats">
                    <!-- Stats will be populated by JavaScript -->
                </div>
            </div>
        </div>

        <script>
            let currentFilename = null;
            
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const progressBar = document.getElementById('progressBar');
            const progressFill = document.getElementById('progressFill');
            const result = document.getElementById('result');
            const videoSection = document.getElementById('videoSection');
            const originalVideo = document.getElementById('originalVideo');
            const analyzeBtn = document.getElementById('analyzeBtn');
            const resultsSection = document.getElementById('resultsSection');

            // Drag and drop functionality
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFile(files[0]);
                }
            });

            function handleFileSelect(event) {
                const file = event.target.files[0];
                if (file) {
                    handleFile(file);
                }
            }

            function handleFile(file) {
                if (!file.type.startsWith('video/')) {
                    showResult('Please select a video file.', 'error');
                    return;
                }

                if (file.size > 500 * 1024 * 1024) {
                    showResult('File size must be less than 500MB.', 'error');
                    return;
                }

                uploadFile(file);
            }

            function uploadFile(file) {
                const formData = new FormData();
                formData.append('file', file);

                progressBar.style.display = 'block';
                result.style.display = 'none';
                videoSection.classList.add('hidden');
                resultsSection.classList.add('hidden');

                const xhr = new XMLHttpRequest();

                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        progressFill.style.width = percentComplete + '%';
                    }
                });

                xhr.addEventListener('load', () => {
                    progressBar.style.display = 'none';
                    
                    if (xhr.status === 200) {
                        const response = JSON.parse(xhr.responseText);
                        currentFilename = response.filename;
                        showResult(`✅ Upload successful! Ready for analysis.`, 'success');
                        
                        // Show video preview
                        const videoUrl = URL.createObjectURL(file);
                        originalVideo.src = videoUrl;
                        videoSection.classList.remove('hidden');
                        analyzeBtn.disabled = false;
                    } else {
                        const error = JSON.parse(xhr.responseText);
                        showResult(`❌ Upload failed: ${error.message || error.error}`, 'error');
                    }
                });

                xhr.addEventListener('error', () => {
                    progressBar.style.display = 'none';
                    showResult('❌ Upload failed: Network error', 'error');
                });

                xhr.open('POST', '/api/upload');
                xhr.send(formData);
            }

            function analyzeVideo() {
                if (!currentFilename) return;
                
                analyzeBtn.disabled = true;
                analyzeBtn.textContent = '🔄 Analyzing...';
                showResult('🔍 Analyzing video for collisions...', 'success');

                fetch(`/api/analyze/${currentFilename}`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    analyzeBtn.disabled = false;
                    analyzeBtn.textContent = '🔍 Analyze for Collisions';
                    
                    if (data.status === 'success') {
                        showResult('✅ Analysis complete! Check results below.', 'success');
                        showResults(data);
                    } else {
                        showResult(`❌ Analysis failed: ${data.message}`, 'error');
                    }
                })
                .catch(error => {
                    analyzeBtn.disabled = false;
                    analyzeBtn.textContent = '🔍 Analyze for Collisions';
                    showResult(`❌ Analysis failed: ${error.message}`, 'error');
                });
            }

            function showResults(data) {
                // Show processed video
                document.getElementById('originalResult').src = originalVideo.src;
                document.getElementById('processedResult').src = `/api/processed/${data.processed_filename}`;
                
                // Show detection stats
                const stats = data.analysis;
                const statsHtml = `
                    <div class="stat-box">
                        <div class="stat-number">${stats.total_frames || 0}</div>
                        <div class="stat-label">Total Frames</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${stats.vehicles_detected || 0}</div>
                        <div class="stat-label">Vehicles Detected</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${stats.collision_warnings || 0}</div>
                        <div class="stat-label">Collision Warnings</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">${stats.processing_time || 'N/A'}</div>
                        <div class="stat-label">Processing Time</div>
                    </div>
                `;
                
                document.getElementById('detectionStats').innerHTML = statsHtml;
                resultsSection.classList.remove('hidden');
            }

            function showResult(message, type) {
                result.textContent = message;
                result.className = `result ${type}`;
                result.style.display = 'block';
            }
        </script>
    </body>
    </html>
    """
    
    @app.route('/')
    def home():
        return COLLISION_HTML
    
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'message': 'Collision Detection Server with Video Analysis',
            'version': '2.0.0',
            'features': ['video_upload', 'collision_detection', 'bounding_boxes', 'yolo_integration']
        })
    
    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Validate file type
            allowed_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.mkv', '.flv', '.webm'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                return jsonify({'error': f'Unsupported file type: {file_ext}'}), 400
            
            # Save file
            import time
            timestamp = int(time.time())
            safe_filename = f"{timestamp}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
            
            file.save(filepath)
            file_size = os.path.getsize(filepath)
            
            logger.info(f"Video uploaded: {safe_filename} ({file_size} bytes)")
            
            return jsonify({
                'status': 'success',
                'message': 'Video uploaded successfully',
                'filename': safe_filename,
                'original_filename': file.filename,
                'size': file_size,
                'type': file_ext
            })
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/analyze/<filename>', methods=['POST'])
    def analyze_video(filename):
        try:
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            if not os.path.exists(input_path):
                return jsonify({'error': 'File not found'}), 404
            
            # Process video
            processed_filename = f"processed_{filename}"
            output_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
            
            start_time = time.time()
            analysis_results = process_video_with_detection(input_path, output_path, detector)
            processing_time = time.time() - start_time
            
            analysis_results['processing_time'] = f"{processing_time:.2f}s"
            
            return jsonify({
                'status': 'success',
                'message': 'Video analysis completed',
                'filename': filename,
                'processed_filename': processed_filename,
                'analysis': analysis_results
            })
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/processed/<filename>')
    def serve_processed_video(filename):
        return send_from_directory(app.config['PROCESSED_FOLDER'], filename)
    
    return app, socketio

def process_video_with_detection(input_path: str, output_path: str, detector: VideoCollisionDetector) -> Dict:
    """Process video with collision detection and return analysis results"""
    cap = cv2.VideoCapture(input_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {input_path}")
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Analysis tracking
    analysis_results = {
        'total_frames': total_frames,
        'vehicles_detected': 0,
        'collision_warnings': 0,
        'frames_with_detections': 0
    }
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame with collision detection
            processed_frame, warning, vehicles = detector.process_frame(frame)
            
            # Update analysis results
            if vehicles:
                analysis_results['frames_with_detections'] += 1
                analysis_results['vehicles_detected'] += len(vehicles)
            
            if warning:
                analysis_results['collision_warnings'] += 1
            
            # Write processed frame
            out.write(processed_frame)
            frame_count += 1
            
            # Log progress every 30 frames
            if frame_count % 30 == 0:
                progress = (frame_count / total_frames) * 100
                logger.info(f"Processing progress: {progress:.1f}% ({frame_count}/{total_frames})")
    
    finally:
        cap.release()
        out.release()
    
    logger.info(f"Video processing complete: {frame_count} frames processed")
    return analysis_results

def main():
    """Main function to start the collision detection server"""
    logger.info("=== Starting Collision Detection Server with Video Analysis ===")
    
    # Check dependencies
    try:
        import cv2
        logger.info(f"✓ OpenCV {cv2.__version__} available")
    except ImportError:
        logger.error("✗ OpenCV not available - required for video processing")
        sys.exit(1)
    
    required_deps = ['flask', 'flask_socketio', 'flask_cors', 'eventlet']
    for dep in required_deps:
        try:
            __import__(dep)
            logger.info(f"✓ {dep} available")
        except ImportError:
            logger.error(f"✗ {dep} not available")
            sys.exit(1)
    
    # Create the application
    app, socketio = create_collision_app()
    
    # Get configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    
    logger.info("Collision detection server configuration:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Upload folder: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"  Processed folder: {app.config['PROCESSED_FOLDER']}")
    logger.info("  Features: Video upload, collision detection, bounding boxes")
    
    try:
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            log_output=False
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()