#!/usr/bin/env python3
"""
Production-ready Collision Detection Server for Google Cloud Platform
Addresses Werkzeug warnings and provides proper production configuration
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

def create_production_app():
    """Create a production-ready Flask application"""
    try:
        from flask import Flask, jsonify, request, send_from_directory
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
    
    # Initialize SocketIO with eventlet for production
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*", 
        async_mode='eventlet',
        logger=False,
        engineio_logger=False
    )
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Root endpoint
    @app.route('/')
    def home():
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Collision Detection System</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                .header { background: #4CAF50; color: white; padding: 20px; border-radius: 10px; text-align: center; }
                .content { background: #f9f9f9; padding: 20px; border-radius: 10px; margin-top: 20px; }
                .status { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0; }
                .button { background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px; display: inline-block; }
                .button:hover { background: #45a049; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚗 Collision Detection System</h1>
                <p>Production Server - Google Cloud Platform</p>
            </div>
            <div class="content">
                <div class="status">
                    <h3>✅ Server Status: Running</h3>
                    <p>The collision detection server is running in production mode on Google Cloud Platform.</p>
                </div>
                <h3>API Endpoints:</h3>
                <a href="/api/health" class="button">Health Check</a>
                <a href="/api/system/info" class="button">System Info</a>
                <a href="/api/status" class="button">Server Status</a>
                
                <h3>Features:</h3>
                <ul>
                    <li>✅ RESTful API</li>
                    <li>✅ WebSocket Support</li>
                    <li>✅ File Upload</li>
                    <li>✅ Production Configuration</li>
                    <li>✅ CORS Enabled</li>
                </ul>
            </div>
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
            'environment': 'production',
            'server': 'Google Cloud Platform',
            'timestamp': '2024-01-01T00:00:00Z'
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
            'features': {
                'api': True,
                'websocket': True,
                'file_upload': True,
                'cors': True,
                'production_ready': True
            }
        })
    
    # Server status endpoint
    @app.route('/api/status')
    def server_status():
        return jsonify({
            'status': 'running',
            'mode': 'production',
            'debug': False,
            'async_mode': 'eventlet',
            'cors_enabled': True,
            'upload_enabled': True
        })
    
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
            logger.error(f"Upload error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # Basic collision detection simulation
    @app.route('/api/collision/detect', methods=['POST'])
    def detect_collision():
        try:
            return jsonify({
                'status': 'success',
                'message': 'Collision detection simulation',
                'detections': [],
                'timestamp': '2024-01-01T00:00:00Z',
                'note': 'Production server running successfully'
            })
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # WebSocket event handlers
    @socketio.on('connect')
    def handle_connect():
        logger.info('Client connected via WebSocket')
        socketio.emit('status', {
            'message': 'Connected to collision detection server',
            'server': 'Google Cloud Platform',
            'mode': 'production',
            'timestamp': '2024-01-01T00:00:00Z'
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected from WebSocket')
    
    @socketio.on('ping')
    def handle_ping():
        socketio.emit('pong', {
            'message': 'Server is alive',
            'timestamp': '2024-01-01T00:00:00Z'
        })
    
    @socketio.on('test')
    def handle_test(data):
        logger.info(f'Test message received: {data}')
        socketio.emit('test_response', {
            'message': 'Test successful',
            'received': data,
            'timestamp': '2024-01-01T00:00:00Z'
        })
    
    return app, socketio

def main():
    """Main function to start the production server"""
    logger.info("=== Starting Production Collision Detection Server ===")
    
    # Check required dependencies
    required_deps = ['flask', 'flask_socketio', 'flask_cors', 'eventlet']
    for dep in required_deps:
        try:
            __import__(dep)
            logger.info(f"✓ {dep} available")
        except ImportError:
            logger.error(f"✗ {dep} not available - required for production")
            sys.exit(1)
    
    # Create the application
    app, socketio = create_production_app()
    
    # Get configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    
    logger.info("Production server configuration:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Environment: production")
    logger.info(f"  Debug: False")
    logger.info(f"  Async mode: eventlet")
    logger.info(f"  Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    logger.info("=== Starting Production Server ===")
    
    try:
        # Run with eventlet for production
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False,
            use_reloader=False,
            log_output=False  # Suppress Werkzeug logs
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        logger.info("Production server shutdown complete")

if __name__ == "__main__":
    main()