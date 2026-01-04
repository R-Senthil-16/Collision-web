#!/bin/bash

# GCP Deployment Fix Script
# Run this INSIDE your Google Cloud VM

echo "=== Fixing Google Cloud Deployment Issues ==="
echo ""

# Get current directory
CURRENT_DIR=$(pwd)
echo "Current directory: $CURRENT_DIR"

# Navigate to the correct directory
cd ~/Collision-web/raspberry-pi || {
    echo "Error: Could not find Collision-web directory"
    echo "Please make sure you cloned the repository to ~/Collision-web"
    exit 1
}

echo "Working directory: $(pwd)"

# Stop any running services
echo "Stopping existing services..."
sudo systemctl stop collision-detection 2>/dev/null || true
pkill -f "collision_server" 2>/dev/null || true

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate || {
    echo "Error: Virtual environment not found. Creating new one..."
    python3 -m venv venv
    source venv/bin/activate
}

# Install/reinstall critical dependencies
echo "Installing/updating Python dependencies..."
pip install --upgrade pip

# Install OpenCV and computer vision dependencies
echo "Installing OpenCV and computer vision libraries..."
sudo apt update
sudo apt install -y python3-opencv libopencv-dev
sudo apt install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1

# Install Python packages with specific versions that work well
pip install opencv-python==4.8.1.78
pip install opencv-contrib-python==4.8.1.78
pip install numpy==1.24.3
pip install flask==2.3.3
pip install flask-socketio==5.3.6
pip install flask-cors==4.0.0
pip install python-dotenv==1.0.0
pip install gunicorn==21.2.0
pip install eventlet==0.33.3

# Install other required packages
pip install -r requirements-minimal.txt 2>/dev/null || echo "requirements-minimal.txt not found, continuing..."

# Create/update environment file
echo "Configuring environment..."
cp .env.example .env 2>/dev/null || echo "Creating new .env file..."

# Update .env with production settings
cat > .env << EOF
# Production Configuration for Google Cloud
HOST=0.0.0.0
PORT=5000
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
UPLOAD_FOLDER=/home/$(whoami)/collision-uploads
LOG_DIRECTORY=/home/$(whoami)/collision-logs

# Hardware Configuration
DISCOVERY_PORT=8888
COMMAND_PORT=8889
STATUS_PORT=8890
NETWORK_TIMEOUT=5.0
DISCOVERY_INTERVAL=30.0

# Resource Configuration
RESOURCE_CONFIG=cloud
EOF

# Create required directories
echo "Creating required directories..."
mkdir -p ~/collision-uploads ~/collision-logs
chmod 755 ~/collision-uploads ~/collision-logs

# Test Python imports
echo "Testing Python imports..."
python3 -c "
import sys
print('Python version:', sys.version)

try:
    import cv2
    print('✓ OpenCV version:', cv2.__version__)
except ImportError as e:
    print('✗ OpenCV import failed:', e)

try:
    import flask
    print('✓ Flask version:', flask.__version__)
except ImportError as e:
    print('✗ Flask import failed:', e)

try:
    import flask_socketio
    print('✓ Flask-SocketIO version:', flask_socketio.__version__)
except ImportError as e:
    print('✗ Flask-SocketIO import failed:', e)
"

# Create a production-ready startup script
echo "Creating production startup script..."
cat > start_server.py << 'EOF'
#!/usr/bin/env python3
"""
Production startup script for Collision Detection Server on Google Cloud
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

def main():
    """Start the collision detection server in production mode"""
    try:
        # Import after environment setup
        from collision_server.main import create_app
        
        app, socketio, hardware_controller, status_monitor, resource_manager, system_monitor = create_app()
        
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5000))
        
        logger.info(f"Starting Collision Detection Server on {host}:{port}")
        logger.info("Production mode enabled")
        
        # Start all components
        resource_manager.start()
        system_monitor.start()
        hardware_controller.start()
        status_monitor.start()
        
        # Update component status
        system_monitor.update_component_status('web_server', 'healthy')
        system_monitor.update_component_status('hardware_controller', 'healthy')
        system_monitor.update_component_status('status_monitor', 'healthy')
        
        logger.info("All components started successfully")
        
        # Run with production WSGI server
        socketio.run(
            app, 
            host=host, 
            port=port, 
            debug=False,
            use_reloader=False,
            log_output=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            system_monitor.stop()
            resource_manager.stop()
            hardware_controller.stop()
            status_monitor.stop()
        except:
            pass

if __name__ == "__main__":
    main()
EOF

chmod +x start_server.py

# Create systemd service file
echo "Creating systemd service..."
sudo tee /etc/systemd/system/collision-detection.service > /dev/null << EOF
[Unit]
Description=Collision Detection Server
After=network.target

[Service]
Type=simple
User=$(whoami)
Group=$(whoami)
WorkingDirectory=/home/$(whoami)/Collision-web/raspberry-pi
Environment=PATH=/home/$(whoami)/Collision-web/raspberry-pi/venv/bin
ExecStart=/home/$(whoami)/Collision-web/raspberry-pi/venv/bin/python /home/$(whoami)/Collision-web/raspberry-pi/production_server.py
Restart=always
RestartSec=10

EnvironmentFile=/home/$(whoami)/Collision-web/raspberry-pi/.env

StandardOutput=journal
StandardError=journal
SyslogIdentifier=collision-detection

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable collision-detection

# Copy the production server script
echo "Setting up production server script..."
cp ~/Collision-web/scripts/gcp-production-server.py ./production_server.py
chmod +x production_server.py

# Copy the simple web interface
mkdir -p static
cp ~/Collision-web/scripts/gcp-simple-web.html ./static/index.html

# Test the server manually first
echo ""
echo "=== Testing Server Startup ==="
echo "Testing server startup (this may take a moment)..."

timeout 30 python3 production_server.py &
SERVER_PID=$!
sleep 10

if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✓ Server started successfully!"
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
else
    echo "✗ Server failed to start. Check the logs above."
fi

echo ""
echo "=== Starting Service ==="
sudo systemctl start collision-detection

# Wait a moment for service to start
sleep 5

# Check service status
echo "Service status:"
sudo systemctl status collision-detection --no-pager -l

echo ""
echo "=== Deployment Fix Complete ==="
echo ""
echo "Next steps:"
echo "1. Check if service is running: sudo systemctl status collision-detection"
echo "2. View logs: sudo journalctl -u collision-detection -f"
echo "3. Get your external IP: curl -s http://checkip.amazonaws.com"
echo "4. Test access: http://YOUR-EXTERNAL-IP:5000/api/health"
echo ""
echo "If you still have issues, run: sudo journalctl -u collision-detection -f"