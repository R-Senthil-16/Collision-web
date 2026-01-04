#!/usr/bin/env python3
"""
Production-ready Collision Detection Server for Google Cloud Platform
Handles import errors gracefully and provides fallback functionality
"""
import os
import sys
import logging
import traceback
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/collision-server.log')
    ]
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """Check and report on critical dependencies"""
    dependencies = {}
    
    # Check Flask
    try:
        import flask
        dependencies['flask'] = flask.__version__
        logger.info(f"✓ Flask {flask.__version__} available")
    except ImportError as e:
        logger.error(f"✗ Flask not available: {e}")
        return False
    
    # Check Flask-SocketIO
    try:
        import flask_socketio
        dependencies['flask_socketio'] = flask_socketio.__version__
        logger.info(f"✓ Flask-SocketIO {flask_socketio.__version__} available")
    except ImportError as e:
        logger.error(f"✗ Flask-SocketIO not available: {e}")
        return False
    
    # Check OpenCV (optional but preferred)
    try:
        import cv2
        dependencies['opencv'] = cv2.__version__
        logger.info(f"✓ OpenCV {cv2.__version__} available")
    except ImportError as e:
        logger.warning(f"⚠ OpenCV not available: {e}")
        logger.warning("Computer vision features will be limited")
    
    # Check other dependencies
    optional_deps = ['numpy', 'flask_cors', 'eventlet']
    for dep in optional_deps:
        try:
            module = __import__(dep)
            version = getattr(module, '__version__', 'unknown')
            dependencies[dep] = version
            logger.info(f"✓ {dep} {version} available")
        except ImportError:
            logger.warning(f"⚠ {dep} not available")
    
    return True

def create_minimal_app():
    """Create a minimal Flask app with basic functionality"""
    from flask import Flask, jsonify, request
    from flask_socketio import SocketIO
    from flask_cors import CORS
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', '/tmp/collision_uploads')
    
    # Enable CORS
    CORS(app, origins="*")
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Basic health check endpoint
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'message': 'Collision Detection Server is running',
            'version': '1.0.0',
            'mode': 'production'
        })
    
    # Basic system info endpoint
    @app.route('/api/system/info')
    def system_info():
        return jsonify({
            'server': 'Google Cloud Platform',
            'python_version': sys.version,
            'upload_folder': app.config['UPLOAD_FOLDER'],
            'max_content_length': app.config['MAX_CONTENT_LENGTH']
        })
    
    # WebSocket connection handler
    @socketio.on('connect')
    def handle_connect():
        logger.info('Client connected')
        socketio.emit('status', {'message': 'Connected to collision detection server'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected')
    
    return app, socketio

def create_full_app():
    """Create the full application with all features"""
    try:
        # Add the src directory to Python path
        src_path = os.path.join(os.path.dirname(__file__), '..', 'raspberry-pi', 'src')
        if os.path.exists(src_path):
            sys.path.insert(0, src_path)
        
        from collision_server.main import create_app
        return create_app()
    except Exception as e:
        logger.error(f"Failed to create full app: {e}")
        logger.error(traceback.format_exc())
        return None

def main():
    """Main function to start the server"""
    logger.info("=== Starting Collision Detection Server ===")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Critical dependencies missing. Cannot start server.")
        sys.exit(1)
    
    # Try to create full app first, fall back to minimal app
    app_components = create_full_app()
    
    if app_components and len(app_components) >= 2:
        logger.info("Using full application with all features")
        app, socketio = app_components[0], app_components[1]
        
        # Start additional components if available
        if len(app_components) > 2:
            try:
                hardware_controller, status_monitor, resource_manager, system_monitor = app_components[2:6]
                
                # Start components
                resource_manager.start()
                system_monitor.start()
                hardware_controller.start()
                status_monitor.start()
                
                # Update component status
                system_monitor.update_component_status('web_server', 'healthy')
                system_monitor.update_component_status('hardware_controller', 'healthy')
                system_monitor.update_component_status('status_monitor', 'healthy')
                
                logger.info("All system components started successfully")
            except Exception as e:
                logger.warning(f"Some components failed to start: {e}")
    else:
        logger.warning("Using minimal application (limited features)")
        app, socketio = create_minimal_app()
    
    # Get configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Server configuration:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Debug: {debug}")
    logger.info(f"  Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    try:
        logger.info("Starting server...")
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
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    main()