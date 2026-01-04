#!/usr/bin/env python3
"""
Minimal Collision Detection Server for Google Cloud Platform
This version handles import errors gracefully and provides basic functionality
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

def create_minimal_server():
    """Create a minimal Flask server with basic collision detection API"""
    try:
        from flask import Flask, jsonify, request, send_from_directory
        from flask_socketio import SocketIO
        from flask_cors import CORS
    except ImportError as e:
        logger.error(f"Failed to import Flask dependencies: {e}")
        sys.exit(1)
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', '/tmp/collision_uploads')
    
    # Enable CORS
    CORS(app, origins="*")
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Serve static files (web interface)
    @app.route('/')
    def serve_index():
        try:
            return send_from_directory('static', 'index.html')
        except:
            return """
            <!DOCTYPE html>
            <html>
            <head><title>Collision Detection Server</title></head>
            <body>
                <h1>🚗 Collision Detection Server</h1>
                <p>Server is running on Google Cloud Platform</p>
                <p><a href="/api/health">Check API Health</a></p>
                <p><a href="/api/system/info">System Information</a></p>
            </body>
            </html>
            """
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'message': 'Collision Detection Server is running',
            'version': '1.0.0',
            'mode': 'production',
            'server': 'Google Cloud Platform'
        })
    
    # System info endpoint
    @app.route('/api/system/info')
    def system_info():
        return jsonify({
            'server': 'Google Cloud Platform',
            'python_version': sys.version,
            'upload_folder': app.config['UPLOAD_FOLDER'],
            'environment': 'production',
            'features': {
                'basic_api': True,
                'websocket': True,
                'file_upload': True,
                'computer_vision': False  # Will be enabled when OpenCV is available
            }
        })
    
    # Basic collision detection endpoint (simulation)
    @app.route('/api/collision/detect', methods=['POST'])
    def detect_collision():
        try:
            # This is a basic simulation - in full version this would use computer vision
            return jsonify({
                'status': 'success',
                'message': 'Collision detection simulation',
                'detections': [],
                'timestamp': '2024-01-01T00:00:00Z',
                'note': 'This is a basic simulation. Full computer vision features require OpenCV.'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # File upload endpoint
    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Save file
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            return jsonify({
                'status': 'success',
                'message': 'File uploaded successfully',
                'filename': filename,
                'size': os.path.getsize(filepath)
            })
        except Exception as e:
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
            'server': 'Google Cloud Platform',
            'timestamp': '2024-01-01T00:00:00Z'
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected from WebSocket')
    
    @socketio.on('ping')
    def handle_ping():
        socketio.emit('pong', {'message': 'Server is alive'})
    
    return app, socketio

def main():
    """Main function to start the server"""
    logger.info("=== Starting Minimal Collision Detection Server ===")
    
    # Check Flask availability
    try:
        import flask
        logger.info(f"✓ Flask {flask.__version__} available")
    except ImportError:
        logger.error("✗ Flask not available - cannot start server")
        sys.exit(1)
    
    # Check optional dependencies
    optional_deps = {
        'cv2': 'OpenCV (computer vision)',
        'numpy': 'NumPy (numerical computing)',
        'PIL': 'Pillow (image processing)'
    }
    
    for dep, description in optional_deps.items():
        try:
            __import__(dep)
            logger.info(f"✓ {description} available")
        except ImportError:
            logger.warning(f"⚠ {description} not available - some features will be limited")
    
    # Create and configure the app
    app, socketio = create_minimal_server()
    
    # Get configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Server configuration:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Debug: {debug}")
    logger.info(f"  Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    logger.info("=== Server Starting ===")
    
    try:
        socketio.run(
            app, 
            host=host, 
            port=port, 
            debug=debug,
            use_reloader=False,
            log_output=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    main()