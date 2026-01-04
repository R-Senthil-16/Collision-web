"""
Main entry point for the Collision Detection Server
"""
import os
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from dotenv import load_dotenv

from .api import create_api_blueprint, init_video_processor
from .websocket import setup_websocket_handlers
from .hardware_controller import HardwareController
from .status_monitor import StatusMonitor
from .resource_manager import create_resource_manager, ResourceManager
from .system_monitor import SystemMonitor


def create_app():
    """Create and configure the Flask application"""
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
    app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', '/tmp/collision_uploads')
    
    # Enable CORS for cross-origin requests from web interface
    CORS(app, origins=["http://localhost:3000", "http://localhost:8080"])
    
    # Initialize SocketIO for real-time communication
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize hardware controller
    hardware_config = {
        'log_directory': os.getenv('LOG_DIRECTORY', '/tmp/collision_logs'),
        'discovery_port': int(os.getenv('DISCOVERY_PORT', 8888)),
        'command_port': int(os.getenv('COMMAND_PORT', 8889)),
        'status_port': int(os.getenv('STATUS_PORT', 8890)),
        'network_timeout': float(os.getenv('NETWORK_TIMEOUT', 5.0)),
        'discovery_interval': float(os.getenv('DISCOVERY_INTERVAL', 30.0))
    }
    hardware_controller = HardwareController(hardware_config)
    
    # Initialize resource manager
    resource_config = os.getenv('RESOURCE_CONFIG', 'default')
    resource_manager = create_resource_manager(resource_config)
    
    # Initialize status monitor
    status_monitor = StatusMonitor(hardware_controller, update_interval=10.0)
    
    # Initialize system monitor
    system_monitor = SystemMonitor(hardware_config['log_directory'])
    
    # Setup WebSocket handlers first
    setup_websocket_handlers(socketio, hardware_controller, status_monitor)
    
    # Define frame callback for real-time streaming
    def frame_callback(camera_id, frame_data, metadata):
        """Callback for streaming camera frames via WebSocket"""
        socketio.emit_camera_frame(camera_id, frame_data, metadata.get('detections'))
    
    # Initialize video processor with collision detection and frame streaming
    init_video_processor(app.config['UPLOAD_FOLDER'], frame_callback)
    
    # Register API blueprint
    api_blueprint = create_api_blueprint(hardware_controller, status_monitor)
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    # Setup WebSocket handlers (already done above)
    # setup_websocket_handlers(socketio, hardware_controller, status_monitor)
    
    # Store instances in app config for access by other modules
    app.config['SOCKETIO'] = socketio
    app.config['HARDWARE_CONTROLLER'] = hardware_controller
    app.config['STATUS_MONITOR'] = status_monitor
    app.config['RESOURCE_MANAGER'] = resource_manager
    app.config['SYSTEM_MONITOR'] = system_monitor
    
    return app, socketio, hardware_controller, status_monitor, resource_manager, system_monitor


def main():
    """Main function to start the collision detection server"""
    app, socketio, hardware_controller, status_monitor, resource_manager, system_monitor = create_app()
    
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Collision Detection Server on {host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print("Collision detection engine initialized and ready")
    
    # Start resource manager first
    resource_manager.start()
    
    # Start system monitor
    system_monitor.start()
    
    # Start hardware controller and status monitor
    hardware_controller.start()
    status_monitor.start()
    
    # Update system monitor with component status
    system_monitor.update_component_status('web_server', 'healthy')
    system_monitor.update_component_status('hardware_controller', 'healthy')
    system_monitor.update_component_status('status_monitor', 'healthy')
    
    # Discover and connect to devices
    hardware_controller.connect_devices()
    
    try:
        socketio.run(app, host=host, port=port, debug=debug)
    finally:
        # Cleanup on shutdown
        system_monitor.stop()
        resource_manager.stop()
        hardware_controller.stop()
        status_monitor.stop()


if __name__ == "__main__":
    main()