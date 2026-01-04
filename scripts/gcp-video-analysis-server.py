#!/usr/bin/env python3
"""
Enhanced Collision Detection Server with Video Upload and Analysis
Integrates YOLO-based collision detection with video upload functionality
"""
import os
import sys
import logging
import time
import json
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any
import threading

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
    """Parameters for collision detection"""
    confidence_threshold: float = 0.5
    vehicle_classes: List[int] = None
    head_on_threshold: float = 0.12
    head_on_color: Tuple[int, int, int] = (0, 0, 255)
    safe_color: Tuple[int, int, int] = (0, 255, 0)
    warning_thickness: int = 3
    safe_thickness: int = 2
    text_scale: float = 0.7
    text_thickness: int = 2
    
    def __post_init__(self):
        if self.vehicle_classes is None:
            self.vehicle_classes = [2, 3, 5, 7]  # COCO class IDs for vehicles

class VideoCollisionAnalyzer:
    """Analyzes uploaded videos for collision detection"""
    
    def __init__(self, upload_folder: str):
        self.upload_folder = upload_folder
        self.params = DetectionParams()
        self.model = None
        self.analysis_results = {}
        
        # Try to initialize YOLO model
        self._init_model()
    
    def _init_model(self):
        """Initialize YOLO model if available"""
        try:
            # Try to import required packages
            import cv2
            import numpy as np
            from ultralytics import YOLO
            
            # Try to load model
            model_path = 'yolov8n.pt'
            if os.path.exists(model_path):
                self.model = YOLO(model_path)
                logger.info("✓ YOLO model loaded successfully")
            else:
                logger.warning("⚠ YOLO model file not found, using simulation mode")
                
        except ImportError as e:
            logger.warning(f"⚠ Computer vision packages not available: {e}")
            logger.warning("⚠ Running in simulation mode")
        except Exception as e:
            logger.warning(f"⚠ Could not initialize YOLO model: {e}")
    
    def analyze_video(self, filename: str) -> Dict[str, Any]:
        """Analyze a video file for collisions"""
        filepath = os.path.join(self.upload_folder, filename)
        
        if not os.path.exists(filepath):
            return {'error': 'File not found'}
        
        # If model is available, do real analysis
        if self.model is not None:
            return self._analyze_with_yolo(filepath, filename)
        else:
            return self._simulate_analysis(filepath, filename)
    
    def _analyze_with_yolo(self, filepath: str, filename: str) -> Dict[str, Any]:
        """Real YOLO-based video analysis"""
        try:
            import cv2
            import numpy as np
            
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return {'error': 'Could not open video file'}
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Analysis variables
            total_detections = 0
            collision_warnings = 0
            vehicles_detected = set()
            frame_analysis = []
            
            # Process every 10th frame for efficiency
            frame_skip = max(1, int(fps / 3)) if fps > 0 else 10
            
            frame_num = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_num % frame_skip == 0:
                    # Run YOLO detection
                    results = self.model(frame, verbose=False)
                    
                    frame_vehicles = []
                    frame_warnings = False
                    
                    # Process detections
                    for result in results:
                        for box in result.boxes:
                            if (int(box.cls[0]) in self.params.vehicle_classes and
                                float(box.conf[0]) > self.params.confidence_threshold):
                                
                                class_name = self.model.names[int(box.cls[0])]
                                vehicles_detected.add(class_name)
                                total_detections += 1
                                
                                # Check for collision warning
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                center_x = (x1 + x2) // 2
                                center_y = (y1 + y2) // 2
                                
                                # Simple collision detection logic
                                frame_center_x = width // 2
                                horizontal_offset = abs(center_x - frame_center_x) / (width / 2.0)
                                vertical_proximity = y2 / height
                                box_area = (x2 - x1) * (y2 - y1)
                                size_factor = box_area / (width * height)
                                
                                if (vertical_proximity > 0.6 and 
                                    horizontal_offset < 0.3 and 
                                    size_factor > 0.05):
                                    frame_warnings = True
                                    collision_warnings += 1
                                
                                frame_vehicles.append({
                                    'class': class_name,
                                    'confidence': float(box.conf[0]),
                                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                    'center': [center_x, center_y]
                                })
                    
                    if frame_vehicles:  # Only store frames with detections
                        frame_analysis.append({
                            'frame': frame_num,
                            'timestamp': frame_num / fps if fps > 0 else 0,
                            'vehicles': frame_vehicles,
                            'collision_warning': frame_warnings
                        })
                
                frame_num += 1
            
            cap.release()
            
            # Calculate statistics
            collision_risk_score = min(1.0, collision_warnings / max(1, len(frame_analysis)))
            
            result = {
                'status': 'success',
                'filename': filename,
                'analysis_type': 'yolo_detection',
                'video_info': {
                    'duration_seconds': round(duration, 2),
                    'fps': round(fps, 2),
                    'resolution': f"{width}x{height}",
                    'total_frames': frame_count,
                    'analyzed_frames': len(frame_analysis)
                },
                'detection_summary': {
                    'total_vehicle_detections': total_detections,
                    'collision_warnings': collision_warnings,
                    'unique_vehicle_types': list(vehicles_detected),
                    'collision_risk_score': round(collision_risk_score, 3),
                    'risk_level': self._get_risk_level(collision_risk_score)
                },
                'frame_analysis': frame_analysis[:50],  # Limit to first 50 frames with detections
                'analysis_timestamp': time.time()
            }
            
            # Store result
            self.analysis_results[filename] = result
            return result
            
        except Exception as e:
            logger.error(f"YOLO analysis error: {e}")
            return {'error': f'Analysis failed: {str(e)}'}
    
    def _simulate_analysis(self, filepath: str, filename: str) -> Dict[str, Any]:
        """Simulate video analysis when YOLO is not available"""
        try:
            # Get basic file info
            file_size = os.path.getsize(filepath)
            
            # Simulate analysis results
            result = {
                'status': 'success',
                'filename': filename,
                'analysis_type': 'simulation',
                'video_info': {
                    'duration_seconds': 45.2,
                    'fps': 30.0,
                    'resolution': '1920x1080',
                    'file_size_mb': round(file_size / (1024*1024), 2)
                },
                'detection_summary': {
                    'total_vehicle_detections': 23,
                    'collision_warnings': 2,
                    'unique_vehicle_types': ['car', 'truck', 'motorcycle'],
                    'collision_risk_score': 0.087,
                    'risk_level': 'low'
                },
                'simulation_note': 'This is simulated data. Install OpenCV and YOLO for real analysis.',
                'analysis_timestamp': time.time()
            }
            
            # Store result
            self.analysis_results[filename] = result
            return result
            
        except Exception as e:
            return {'error': f'Simulation failed: {str(e)}'}
    
    def _get_risk_level(self, score: float) -> str:
        """Convert risk score to human-readable level"""
        if score < 0.1:
            return 'low'
        elif score < 0.3:
            return 'medium'
        else:
            return 'high'
    
    def get_analysis_result(self, filename: str) -> Dict[str, Any]:
        """Get stored analysis result"""
        return self.analysis_results.get(filename, {'error': 'Analysis not found'})

def create_video_analysis_app():
    """Create Flask app with video upload and analysis"""
    try:
        from flask import Flask, jsonify, request, send_from_directory
        from flask_socketio import SocketIO, emit
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
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
    
    # Production settings
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
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
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize video analyzer
    analyzer = VideoCollisionAnalyzer(app.config['UPLOAD_FOLDER'])
    
    # Enhanced HTML template with analysis features
    VIDEO_ANALYSIS_HTML = """
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
            .section { 
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
            .upload-area.dragover {
                border-color: #4CAF50;
                background-color: #e8f5e8;
            }
            .file-input { display: none; }
            .btn {
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
            .btn:hover { background: #764ba2; }
            .btn.analyze { background: #4CAF50; }
            .btn.analyze:hover { background: #45a049; }
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
            .analysis-result {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
                display: none;
            }
            .risk-low { color: #28a745; font-weight: bold; }
            .risk-medium { color: #ffc107; font-weight: bold; }
            .risk-high { color: #dc3545; font-weight: bold; }
            .video-preview {
                max-width: 100%;
                border-radius: 8px;
                margin-top: 20px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .stat-card {
                background: white;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                border: 1px solid #e0e0e0;
            }
            .stat-value {
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
            }
            .stat-label {
                color: #666;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚗 Collision Detection System</h1>
            <p>AI-Powered Video Analysis with YOLO Detection</p>
        </div>

        <div class="section">
            <h2>📹 Upload & Analyze Video</h2>
            <div class="upload-area" id="uploadArea">
                <div>
                    <h3>Drop your video file here</h3>
                    <p>or</p>
                    <button class="btn" onclick="document.getElementById('fileInput').click()">
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
            
            <video id="videoPreview" class="video-preview" controls style="display: none;"></video>
            
            <div id="analyzeSection" style="display: none; text-align: center; margin-top: 20px;">
                <button class="btn analyze" onclick="analyzeVideo()">
                    🔍 Analyze for Collisions
                </button>
            </div>
            
            <div class="analysis-result" id="analysisResult"></div>
        </div>

        <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
        <script>
            let currentFilename = null;
            let socket = null;
            
            // Initialize WebSocket connection
            function initSocket() {
                socket = io();
                socket.on('connect', () => {
                    console.log('Connected to server');
                });
                
                socket.on('analysis_progress', (data) => {
                    console.log('Analysis progress:', data);
                    showResult(`🔄 Analysis progress: ${data.message}`, 'success');
                });
                
                socket.on('analysis_complete', (data) => {
                    console.log('Analysis complete:', data);
                    displayAnalysisResult(data);
                });
            }
            
            // Initialize on page load
            window.onload = function() {
                initSocket();
            };

            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const progressBar = document.getElementById('progressBar');
            const progressFill = document.getElementById('progressFill');
            const result = document.getElementById('result');
            const videoPreview = document.getElementById('videoPreview');
            const analyzeSection = document.getElementById('analyzeSection');
            const analysisResult = document.getElementById('analysisResult');

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
                // Validate file type
                if (!file.type.startsWith('video/')) {
                    showResult('Please select a video file.', 'error');
                    return;
                }

                // Validate file size (500MB)
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
                analysisResult.style.display = 'none';

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
                        showResult(`✅ Upload successful! File: ${response.original_filename} (${formatFileSize(response.size)})`, 'success');
                        
                        // Show video preview
                        const videoUrl = URL.createObjectURL(file);
                        videoPreview.src = videoUrl;
                        videoPreview.style.display = 'block';
                        
                        // Show analyze button
                        analyzeSection.style.display = 'block';
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
                if (!currentFilename) {
                    showResult('No video uploaded for analysis', 'error');
                    return;
                }
                
                showResult('🔄 Starting collision detection analysis...', 'success');
                
                fetch(`/api/analyze/${currentFilename}`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        displayAnalysisResult(data);
                    } else {
                        showResult(`❌ Analysis failed: ${data.error || data.message}`, 'error');
                    }
                })
                .catch(error => {
                    showResult(`❌ Analysis error: ${error.message}`, 'error');
                });
            }
            
            function displayAnalysisResult(data) {
                const container = document.getElementById('analysisResult');
                
                let html = `
                    <h3>🔍 Collision Detection Analysis Results</h3>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">${data.detection_summary.total_vehicle_detections}</div>
                            <div class="stat-label">Vehicle Detections</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.detection_summary.collision_warnings}</div>
                            <div class="stat-label">Collision Warnings</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value risk-${data.detection_summary.risk_level}">${data.detection_summary.risk_level.toUpperCase()}</div>
                            <div class="stat-label">Risk Level</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${data.detection_summary.collision_risk_score}</div>
                            <div class="stat-label">Risk Score</div>
                        </div>
                    </div>
                    
                    <h4>📊 Video Information</h4>
                    <p><strong>Duration:</strong> ${data.video_info.duration_seconds}s</p>
                    <p><strong>Resolution:</strong> ${data.video_info.resolution}</p>
                    <p><strong>FPS:</strong> ${data.video_info.fps}</p>
                    
                    <h4>🚗 Detected Vehicles</h4>
                    <p>${data.detection_summary.unique_vehicle_types.join(', ')}</p>
                `;
                
                if (data.analysis_type === 'simulation') {
                    html += `<p style="color: #ffc107; font-weight: bold;">⚠️ ${data.simulation_note}</p>`;
                }
                
                container.innerHTML = html;
                container.style.display = 'block';
                
                showResult('✅ Analysis complete! Results displayed below.', 'success');
            }

            function showResult(message, type) {
                result.textContent = message;
                result.className = `result ${type}`;
                result.style.display = 'block';
            }

            function formatFileSize(bytes) {
                if (bytes === 0) return '0 Bytes';
                const k = 1024;
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            }
        </script>
    </body>
    </html>
    """
    
    # Root endpoint with video analysis interface
    @app.route('/')
    def home():
        return VIDEO_ANALYSIS_HTML
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'message': 'Collision Detection Server with Video Analysis',
            'version': '2.0.0',
            'environment': 'production',
            'server': 'Google Cloud Platform',
            'features': ['video_upload', 'yolo_detection', 'collision_analysis', 'websocket'],
            'yolo_available': analyzer.model is not None
        })
    
    # System information endpoint
    @app.route('/api/system/info')
    def system_info():
        return jsonify({
            'server': 'Google Cloud Platform',
            'python_version': sys.version.split()[0],
            'flask_mode': 'production',
            'upload_folder': app.config['UPLOAD_FOLDER'],
            'max_upload_size': f"{app.config['MAX_CONTENT_LENGTH'] // (1024*1024)}MB",
            'supported_formats': ['mp4', 'avi', 'mov', 'wmv', 'mkv'],
            'analysis_features': {
                'yolo_detection': analyzer.model is not None,
                'collision_detection': True,
                'vehicle_classification': True,
                'risk_assessment': True,
                'real_time_analysis': True
            }
        })
    
    # Enhanced file upload endpoint
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
                return jsonify({'error': f'Unsupported file type: {file_ext}. Supported: {", ".join(allowed_extensions)}'}), 400
            
            # Save file with timestamp to avoid conflicts
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
                'type': file_ext,
                'upload_time': timestamp
            })
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # Video analysis endpoint - integrates your collision detection code
    @app.route('/api/analyze/<filename>', methods=['POST'])
    def analyze_video(filename):
        try:
            def run_analysis():
                """Run analysis in background thread"""
                socketio.emit('analysis_progress', {'message': 'Starting analysis...'})
                result = analyzer.analyze_video(filename)
                socketio.emit('analysis_complete', result)
            
            # Start analysis in background
            analysis_thread = threading.Thread(target=run_analysis)
            analysis_thread.daemon = True
            analysis_thread.start()
            
            return jsonify({
                'status': 'started',
                'message': 'Analysis started in background',
                'filename': filename
            })
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # Get analysis result endpoint
    @app.route('/api/analysis/<filename>')
    def get_analysis(filename):
        result = analyzer.get_analysis_result(filename)
        return jsonify(result)
    
    # List uploaded files
    @app.route('/api/uploads')
    def list_uploads():
        try:
            files = []
            upload_dir = app.config['UPLOAD_FOLDER']
            
            if os.path.exists(upload_dir):
                for filename in os.listdir(upload_dir):
                    filepath = os.path.join(upload_dir, filename)
                    if os.path.isfile(filepath):
                        stat = os.stat(filepath)
                        files.append({
                            'filename': filename,
                            'size': stat.st_size,
                            'modified': stat.st_mtime,
                            'type': os.path.splitext(filename)[1],
                            'analyzed': filename in analyzer.analysis_results
                        })
            
            return jsonify({
                'status': 'success',
                'files': files,
                'total_files': len(files),
                'upload_folder': upload_dir
            })
            
        except Exception as e:
            logger.error(f"List uploads error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # WebSocket handlers
    @socketio.on('connect')
    def handle_connect():
        logger.info('Client connected via WebSocket')
        emit('status', {
            'message': 'Connected to collision detection server',
            'features': ['video_upload', 'yolo_analysis', 'real_time_updates'],
            'server': 'Google Cloud Platform',
            'yolo_available': analyzer.model is not None
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected from WebSocket')
    
    return app, socketio

def main():
    """Main function to start the enhanced server"""
    logger.info("=== Starting Enhanced Collision Detection Server with YOLO Analysis ===")
    
    # Check dependencies
    required_deps = ['flask', 'flask_socketio', 'flask_cors', 'eventlet']
    for dep in required_deps:
        try:
            __import__(dep)
            logger.info(f"✓ {dep} available")
        except ImportError:
            logger.error(f"✗ {dep} not available")
            sys.exit(1)
    
    # Check optional computer vision dependencies
    optional_deps = ['cv2', 'numpy', 'ultralytics']
    cv_available = True
    for dep in optional_deps:
        try:
            __import__(dep)
            logger.info(f"✓ {dep} available")
        except ImportError:
            logger.warning(f"⚠ {dep} not available - using simulation mode")
            cv_available = False
    
    if cv_available:
        logger.info("🎉 Full YOLO analysis mode enabled!")
    else:
        logger.info("📝 Running in simulation mode - install OpenCV and ultralytics for real analysis")
    
    # Create the application
    app, socketio = create_video_analysis_app()
    
    # Get configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    
    logger.info("Enhanced server configuration:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Upload folder: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"  Max upload size: {app.config['MAX_CONTENT_LENGTH'] // (1024*1024)}MB")
    logger.info("  Features: Video upload, YOLO analysis, collision detection, WebSocket updates")
    
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