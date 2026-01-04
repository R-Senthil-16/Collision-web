#!/usr/bin/env python3
"""
Enhanced Collision Detection Server with Video Upload Support
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_video_upload_app():
    """Create Flask app with video upload support"""
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
    
    # Video upload HTML template
    VIDEO_UPLOAD_HTML = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Collision Detection - Video Upload</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 1000px; 
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
            .upload-section { 
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
            .file-input {
                display: none;
            }
            .upload-btn {
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
            .upload-btn:hover {
                background: #764ba2;
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
            .video-preview {
                max-width: 100%;
                border-radius: 8px;
                margin-top: 20px;
            }
            .api-section {
                background: white;
                padding: 20px;
                border-radius: 15px;
                margin-bottom: 20px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
            .api-btn {
                background: #4CAF50;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin: 5px;
                display: inline-block;
                transition: background 0.3s ease;
            }
            .api-btn:hover {
                background: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚗 Collision Detection System</h1>
            <p>Video Upload & Analysis Platform</p>
        </div>

        <div class="upload-section">
            <h2>📹 Upload Video for Analysis</h2>
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
            
            <video id="videoPreview" class="video-preview" controls style="display: none;"></video>
        </div>

        <div class="api-section">
            <h3>🔗 API Endpoints</h3>
            <a href="/api/health" class="api-btn">Health Check</a>
            <a href="/api/system/info" class="api-btn">System Info</a>
            <a href="/api/uploads" class="api-btn">View Uploads</a>
        </div>

        <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const progressBar = document.getElementById('progressBar');
            const progressFill = document.getElementById('progressFill');
            const result = document.getElementById('result');
            const videoPreview = document.getElementById('videoPreview');

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
                        showResult(`✅ Upload successful! File: ${response.filename} (${formatFileSize(response.size)})`, 'success');
                        
                        // Show video preview
                        const videoUrl = URL.createObjectURL(file);
                        videoPreview.src = videoUrl;
                        videoPreview.style.display = 'block';
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
    
    # Root endpoint with video upload interface
    @app.route('/')
    def home():
        return VIDEO_UPLOAD_HTML
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'message': 'Collision Detection Server with Video Upload',
            'version': '1.1.0',
            'environment': 'production',
            'server': 'Google Cloud Platform',
            'features': ['video_upload', 'collision_detection', 'websocket']
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
            'features': {
                'video_upload': True,
                'drag_drop': True,
                'progress_tracking': True,
                'video_preview': True,
                'collision_detection': True,
                'websocket': True,
                'cors': True
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
                'type': file_ext,
                'upload_time': timestamp
            })
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
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
                            'type': os.path.splitext(filename)[1]
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
    
    # Video analysis endpoint (placeholder)
    @app.route('/api/analyze/<filename>', methods=['POST'])
    def analyze_video(filename):
        try:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            if not os.path.exists(filepath):
                return jsonify({'error': 'File not found'}), 404
            
            # Placeholder for video analysis
            return jsonify({
                'status': 'success',
                'message': 'Video analysis completed',
                'filename': filename,
                'analysis': {
                    'duration': '00:02:30',
                    'resolution': '1920x1080',
                    'fps': 30,
                    'collisions_detected': 0,
                    'objects_detected': ['car', 'person', 'traffic_light'],
                    'confidence': 0.85
                },
                'note': 'This is a simulation. Full analysis requires computer vision setup.'
            })
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # WebSocket handlers
    @socketio.on('connect')
    def handle_connect():
        logger.info('Client connected via WebSocket')
        socketio.emit('status', {
            'message': 'Connected to collision detection server',
            'features': ['video_upload', 'real_time_analysis'],
            'server': 'Google Cloud Platform'
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected from WebSocket')
    
    return app, socketio

def main():
    """Main function to start the enhanced server"""
    logger.info("=== Starting Enhanced Collision Detection Server with Video Upload ===")
    
    # Check dependencies
    required_deps = ['flask', 'flask_socketio', 'flask_cors', 'eventlet']
    for dep in required_deps:
        try:
            __import__(dep)
            logger.info(f"✓ {dep} available")
        except ImportError:
            logger.error(f"✗ {dep} not available")
            sys.exit(1)
    
    # Create the application
    app, socketio = create_video_upload_app()
    
    # Get configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    
    logger.info("Enhanced server configuration:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Upload folder: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"  Max upload size: {app.config['MAX_CONTENT_LENGTH'] // (1024*1024)}MB")
    logger.info("  Features: Video upload, drag & drop, progress tracking")
    
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