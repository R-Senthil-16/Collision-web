#!/usr/bin/env python3
"""
Simplified Collision Detection Server - Fixed Version
Focuses on core video upload and collision detection functionality
"""
import os
import sys
import logging
import cv2
import numpy as np
import time
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DetectionParams:
    confidence_threshold: float = 0.5
    vehicle_classes: List[int] = None
    head_on_threshold: float = 0.12
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
        self.params = params if params is not None else DetectionParams()
        self.model_available = False
        
        # Try to load YOLO model
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.model_available = True
            logger.info(f"✓ YOLO model loaded: {model_path}")
        except ImportError:
            logger.warning("⚠ YOLO not available - using simulation mode")
        except Exception as e:
            logger.warning(f"⚠ YOLO model failed to load: {e} - using simulation mode")
    
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
            if result.boxes is not None:
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
        
        # Calculate threat scores and find best vehicle
        best_vehicle = None
        best_score = 0.0
        height_f = float(height)
        width_f = float(width)
        
        for v in vehicles:
            x1, y1, x2, y2 = v['box']
            center_x, center_y = v['center']
            
            # Threat scoring logic
            vertical_proximity = max(0.0, min(1.0, y2 / height_f))
            horizontal_offset = abs(center_x - frame_center_x) / (width_f / 2.0)
            horizontal_alignment = max(0.0, 1.0 - horizontal_offset)
            box_area = max(1.0, float((x2 - x1) * (y2 - y1)))
            size_factor = min(1.0, box_area / (width_f * height_f * 0.25))
            
            threat_score = (0.5 * vertical_proximity + 0.5 * size_factor) * horizontal_alignment
            v['threat_score'] = threat_score
            
            if threat_score > best_score:
                best_score = threat_score
                best_vehicle = v
        
        # Check for collision warning
        head_on_warning = False
        if best_vehicle is not None:
            bx1, by1, bx2, by2 = best_vehicle['box']
            b_center_x, b_center_y = best_vehicle['center']
            
            vertical_proximity = max(0.0, min(1.0, by2 / height_f))
            horizontal_offset = abs(b_center_x - frame_center_x) / (width_f / 2.0)
            horizontal_alignment = max(0.0, 1.0 - horizontal_offset)
            box_area = max(1.0, float((bx2 - bx1) * (by2 - by1)))
            size_factor = min(1.0, box_area / (width_f * height_f * 0.25))
            
            if (best_score >= self.params.head_on_threshold and
                vertical_proximity > 0.3 and
                horizontal_alignment > 0.35 and
                size_factor > 0.06):
                head_on_warning = True
        
        # Draw detections
        for v in vehicles:
            x1, y1, x2, y2 = v['box']
            label_base = v['class_name']
            conf = v['confidence']
            
            if v is best_vehicle and head_on_warning:
                color = self.params.head_on_color
                thickness = self.params.warning_thickness
                label = f"HEAD-ON RISK: {label_base} {conf:.2f}"
            else:
                color = self.params.safe_color
                thickness = self.params.safe_thickness
                label = f"{label_base} {conf:.2f}"
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label with background
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 
                                       self.params.text_scale, self.params.text_thickness)[0]
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), color, -1)
            
            cv2.putText(frame, label, (x1, max(0, y1 - 10)),
                       cv2.FONT_HERSHEY_SIMPLEX, self.params.text_scale,
                       (255, 255, 255), self.params.text_thickness)
        
        # Add warning overlay if collision detected
        if head_on_warning and best_vehicle is not None:
            warning_text = "WARNING: VEHICLE AHEAD - POTENTIAL COLLISION"
            text_size = cv2.getTextSize(warning_text, cv2.FONT_HERSHEY_SIMPLEX,
                                      self.params.text_scale * 1.2, 
                                      self.params.text_thickness * 2)[0]
            text_x = (width - text_size[0]) // 2
            
            # Background rectangle
            cv2.rectangle(frame, (text_x - 10, 30 - text_size[1] - 10),
                         (text_x + text_size[0] + 10, 50), (0, 0, 0), -1)
            
            # Warning text
            cv2.putText(frame, warning_text, (text_x, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, self.params.text_scale * 1.2,
                       self.params.head_on_color, self.params.text_thickness * 2)
            
            # Red border
            border_size = 10
            frame[0:border_size, :] = self.params.head_on_color
            frame[-border_size:, :] = self.params.head_on_color
            frame[:, 0:border_size] = self.params.head_on_color
            frame[:, -border_size:] = self.params.head_on_color
        
        return frame, head_on_warning, vehicles
    
    def _simulate_detection(self, frame: np.ndarray) -> Tuple[np.ndarray, bool, List[Dict]]:
        """Simulate detection when YOLO is not available"""
        height, width = frame.shape[:2]
        
        # Create fake detection for demo
        vehicles = [{
            'box': (width//4, height//3, width//2, height//2),
            'center': (width//3, height//2.5),
            'class': 2,
            'confidence': 0.85,
            'class_name': 'car',
            'threat_score': 0.15
        }]
        
        # Draw simulated detection
        for v in vehicles:
            x1, y1, x2, y2 = v['box']
            label = f"SIMULATED: {v['class_name']} {v['confidence']:.2f}"
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.params.safe_color, 
                         self.params.safe_thickness)
            cv2.putText(frame, label, (x1, max(0, y1 - 10)),
                       cv2.FONT_HERSHEY_SIMPLEX, self.params.text_scale,
                       self.params.safe_color, self.params.text_thickness)
        
        # Add simulation notice
        cv2.putText(frame, "SIMULATION MODE - Install YOLO for real detection",
                   (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                   (0, 255, 255), 1)
        
        return frame, False, vehicles

def process_video_with_detection(input_path: str, output_path: str, 
                               detector: VideoCollisionDetector) -> Dict:
    """Process video with collision detection"""
    cap = cv2.VideoCapture(input_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {input_path}")
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
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
            
            # Process frame
            processed_frame, warning, vehicles = detector.process_frame(frame)
            
            # Update analysis
            if vehicles:
                analysis_results['frames_with_detections'] += 1
                analysis_results['vehicles_detected'] += len(vehicles)
            
            if warning:
                analysis_results['collision_warnings'] += 1
            
            # Write frame
            out.write(processed_frame)
            frame_count += 1
            
            # Log progress
            if frame_count % 30 == 0:
                progress = (frame_count / max(total_frames, 1)) * 100
                logger.info(f"Processing: {progress:.1f}% ({frame_count}/{total_frames})")
    
    finally:
        cap.release()
        out.release()
    
    logger.info(f"✓ Video processing complete: {frame_count} frames")
    return analysis_results

def create_app():
    """Create Flask app"""
    try:
        from flask import Flask, jsonify, request, send_from_directory
        from flask_cors import CORS
    except ImportError as e:
        logger.error(f"Missing Flask dependencies: {e}")
        sys.exit(1)
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'collision-detection-key'
    app.config['UPLOAD_FOLDER'] = '/tmp/collision_uploads'
    app.config['PROCESSED_FOLDER'] = '/tmp/collision_uploads/processed'
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
    
    # Enable CORS
    CORS(app, origins="*")
    
    # Create directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
    
    # Initialize detector
    detector = VideoCollisionDetector()
    
    # HTML template
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Collision Detection System</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header { background: #667eea; color: white; padding: 20px; border-radius: 10px; text-align: center; }
            .upload-section { background: white; padding: 20px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .upload-area { border: 2px dashed #667eea; padding: 40px; text-align: center; border-radius: 10px; }
            .btn { background: #667eea; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            .btn:hover { background: #5a6fd8; }
            .progress { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; margin: 10px 0; }
            .progress-bar { height: 100%; background: #667eea; width: 0%; transition: width 0.3s; }
            .result { padding: 15px; margin: 10px 0; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            .video-container { display: flex; gap: 20px; margin: 20px 0; }
            .video-box { flex: 1; text-align: center; }
            .video-box video { max-width: 100%; border-radius: 5px; }
            .hidden { display: none; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚗 Collision Detection System</h1>
            <p>Upload videos for AI-powered collision analysis</p>
        </div>
        
        <div class="upload-section">
            <h2>📹 Upload Video</h2>
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <h3>Click to select video file</h3>
                <p>Supported: MP4, AVI, MOV, WMV (Max: 500MB)</p>
                <input type="file" id="fileInput" accept="video/*" style="display: none;" onchange="handleFile(event)">
            </div>
            
            <div class="progress hidden" id="progress">
                <div class="progress-bar" id="progressBar"></div>
            </div>
            
            <div id="result"></div>
            
            <div id="videoSection" class="hidden">
                <video id="originalVideo" controls style="max-width: 100%; margin: 10px 0;"></video>
                <br>
                <button class="btn" onclick="analyzeVideo()" id="analyzeBtn">🔍 Analyze for Collisions</button>
            </div>
        </div>
        
        <div id="resultsSection" class="hidden">
            <h2>📊 Analysis Results</h2>
            <div class="video-container">
                <div class="video-box">
                    <h4>Original Video</h4>
                    <video id="originalResult" controls></video>
                </div>
                <div class="video-box">
                    <h4>Processed Video (with Detection)</h4>
                    <video id="processedResult" controls></video>
                </div>
            </div>
            <div id="stats"></div>
        </div>
        
        <script>
            let currentFilename = null;
            
            function handleFile(event) {
                const file = event.target.files[0];
                if (!file) return;
                
                if (!file.type.startsWith('video/')) {
                    showResult('Please select a video file', 'error');
                    return;
                }
                
                if (file.size > 500 * 1024 * 1024) {
                    showResult('File too large (max 500MB)', 'error');
                    return;
                }
                
                uploadFile(file);
            }
            
            function uploadFile(file) {
                const formData = new FormData();
                formData.append('file', file);
                
                document.getElementById('progress').classList.remove('hidden');
                
                const xhr = new XMLHttpRequest();
                
                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        const percent = (e.loaded / e.total) * 100;
                        document.getElementById('progressBar').style.width = percent + '%';
                    }
                };
                
                xhr.onload = () => {
                    document.getElementById('progress').classList.add('hidden');
                    
                    if (xhr.status === 200) {
                        const response = JSON.parse(xhr.responseText);
                        currentFilename = response.filename;
                        showResult('✅ Upload successful!', 'success');
                        
                        const videoUrl = URL.createObjectURL(file);
                        document.getElementById('originalVideo').src = videoUrl;
                        document.getElementById('videoSection').classList.remove('hidden');
                    } else {
                        const error = JSON.parse(xhr.responseText);
                        showResult('❌ Upload failed: ' + error.error, 'error');
                    }
                };
                
                xhr.onerror = () => {
                    document.getElementById('progress').classList.add('hidden');
                    showResult('❌ Network error', 'error');
                };
                
                xhr.open('POST', '/api/upload');
                xhr.send(formData);
            }
            
            function analyzeVideo() {
                if (!currentFilename) return;
                
                const btn = document.getElementById('analyzeBtn');
                btn.disabled = true;
                btn.textContent = '🔄 Analyzing...';
                
                fetch('/api/analyze/' + currentFilename, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    btn.disabled = false;
                    btn.textContent = '🔍 Analyze for Collisions';
                    
                    if (data.status === 'success') {
                        showResult('✅ Analysis complete!', 'success');
                        showResults(data);
                    } else {
                        showResult('❌ Analysis failed: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    btn.disabled = false;
                    btn.textContent = '🔍 Analyze for Collisions';
                    showResult('❌ Error: ' + error.message, 'error');
                });
            }
            
            function showResults(data) {
                document.getElementById('originalResult').src = document.getElementById('originalVideo').src;
                document.getElementById('processedResult').src = '/api/processed/' + data.processed_filename;
                
                const stats = data.analysis;
                document.getElementById('stats').innerHTML = 
                    '<h3>Detection Statistics</h3>' +
                    '<p>Total Frames: ' + (stats.total_frames || 0) + '</p>' +
                    '<p>Vehicles Detected: ' + (stats.vehicles_detected || 0) + '</p>' +
                    '<p>Collision Warnings: ' + (stats.collision_warnings || 0) + '</p>' +
                    '<p>Processing Time: ' + (stats.processing_time || 'N/A') + '</p>';
                
                document.getElementById('resultsSection').classList.remove('hidden');
            }
            
            function showResult(message, type) {
                const result = document.getElementById('result');
                result.textContent = message;
                result.className = 'result ' + type;
            }
        </script>
    </body>
    </html>
    """
    
    @app.route('/')
    def home():
        return HTML_TEMPLATE
    
    @app.route('/api/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'message': 'Collision Detection Server',
            'version': '1.0.0',
            'yolo_available': detector.model_available
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
            allowed_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.mkv'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            if file_ext not in allowed_extensions:
                return jsonify({'error': f'Unsupported file type: {file_ext}'}), 400
            
            # Save file
            timestamp = int(time.time())
            safe_filename = f"{timestamp}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
            
            file.save(filepath)
            file_size = os.path.getsize(filepath)
            
            logger.info(f"✓ Video uploaded: {safe_filename} ({file_size} bytes)")
            
            return jsonify({
                'status': 'success',
                'filename': safe_filename,
                'size': file_size
            })
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return jsonify({'error': str(e)}), 500
    
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
                'processed_filename': processed_filename,
                'analysis': analysis_results
            })
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/processed/<filename>')
    def serve_processed_video(filename):
        return send_from_directory(app.config['PROCESSED_FOLDER'], filename)
    
    return app

def main():
    """Main function"""
    logger.info("=== Starting Collision Detection Server ===")
    
    # Check OpenCV
    try:
        import cv2
        logger.info(f"✓ OpenCV {cv2.__version__} available")
    except ImportError:
        logger.error("✗ OpenCV not available")
        sys.exit(1)
    
    # Create app
    app = create_app()
    
    # Get config
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    
    try:
        app.run(host=host, port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()