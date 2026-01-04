#!/bin/bash

# Simple GCP Deployment Fix Script
# Run this INSIDE your Google Cloud VM

echo "=== Simple Collision Detection Server Fix ==="
echo ""

# Get current directory and navigate to project
CURRENT_DIR=$(pwd)
echo "Current directory: $CURRENT_DIR"

# Try to find the project directory
if [ -d "~/Collision-web" ]; then
    cd ~/Collision-web/raspberry-pi
    echo "Found Collision-web directory"
elif [ -d "./raspberry-pi" ]; then
    cd ./raspberry-pi
    echo "Using current directory with raspberry-pi folder"
else
    echo "Error: Could not find project directory"
    echo "Please make sure you're in the Collision-web directory or it exists in your home folder"
    exit 1
fi

echo "Working directory: $(pwd)"

# Stop any running services
echo "Stopping existing services..."
sudo systemctl stop collision-detection 2>/dev/null || true
pkill -f "collision" 2>/dev/null || true
pkill -f "python.*server" 2>/dev/null || true

# Update system packages
echo "Updating system packages..."
sudo apt update

# Install essential Python packages
echo "Installing Python and essential packages..."
sudo apt install -y python3-pip python3-venv python3-dev

# Create or activate virtual environment
echo "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install minimal required packages
echo "Installing minimal Python dependencies..."
pip install --upgrade pip
pip install flask==2.3.3
pip install flask-socketio==5.3.6
pip install flask-cors==4.0.0
pip install python-dotenv==1.0.0
pip install eventlet==0.33.3

# Create environment file
echo "Creating environment configuration..."
cat > .env << EOF
# Minimal Production Configuration
HOST=0.0.0.0
PORT=5000
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "fallback-secret-key-$(date +%s)")
UPLOAD_FOLDER=/home/$(whoami)/collision-uploads
LOG_DIRECTORY=/home/$(whoami)/collision-logs
EOF

# Create required directories
echo "Creating required directories..."
mkdir -p ~/collision-uploads ~/collision-logs
chmod 755 ~/collision-uploads ~/collision-logs

# Copy the minimal server script
echo "Setting up minimal server..."
if [ -f "../scripts/gcp-minimal-server.py" ]; then
    cp ../scripts/gcp-minimal-server.py ./minimal_server.py
else
    echo "Creating minimal server script..."
    cat > minimal_server.py << 'EOFSERVER'
#!/usr/bin/env python3
import os
import sys
from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def home():
    return '''
    <h1>🚗 Collision Detection Server</h1>
    <p>Server is running on Google Cloud Platform</p>
    <p><a href="/api/health">Check Health</a></p>
    '''

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'message': 'Server is running',
        'server': 'Google Cloud Platform'
    })

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    socketio.emit('status', {'message': 'Connected'})

if __name__ == "__main__":
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    print(f"Starting server on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=False)
EOFSERVER
fi

chmod +x minimal_server.py

# Test the server
echo ""
echo "=== Testing Server ==="
echo "Testing server startup..."

# Test Python imports
python3 -c "
try:
    import flask, flask_socketio, flask_cors
    print('✓ All required packages available')
except ImportError as e:
    print(f'✗ Missing package: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "✗ Package test failed"
    exit 1
fi

# Test server startup
timeout 15 python3 minimal_server.py &
SERVER_PID=$!
sleep 8

if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✓ Server started successfully!"
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
else
    echo "✗ Server failed to start"
    exit 1
fi

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/collision-detection.service > /dev/null << EOF
[Unit]
Description=Collision Detection Server (Minimal)
After=network.target

[Service]
Type=simple
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python $(pwd)/minimal_server.py
Restart=always
RestartSec=10

EnvironmentFile=$(pwd)/.env

StandardOutput=journal
StandardError=journal
SyslogIdentifier=collision-detection

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable collision-detection
sudo systemctl start collision-detection

# Wait for service to start
sleep 5

# Check service status
echo ""
echo "=== Service Status ==="
sudo systemctl status collision-detection --no-pager -l

echo ""
echo "=== Fix Complete ==="
echo ""
echo "Next steps:"
echo "1. Configure firewall (run on your LOCAL computer):"
echo "   gcloud compute firewall-rules create allow-port-5000 --allow tcp:5000 --source-ranges 0.0.0.0/0"
echo "   gcloud compute instances add-tags collision-detection-server --tags http-server --zone us-central1-a"
echo ""
echo "2. Get your external IP:"
echo "   gcloud compute instances describe collision-detection-server --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'"
echo ""
echo "3. Test your server:"
echo "   http://YOUR-EXTERNAL-IP:5000"
echo "   http://YOUR-EXTERNAL-IP:5000/api/health"
echo ""
echo "4. View logs if needed:"
echo "   sudo journalctl -u collision-detection -f"