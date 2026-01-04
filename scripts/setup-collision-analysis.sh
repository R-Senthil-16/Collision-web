#!/bin/bash

# Setup Collision Analysis Server on Google Cloud Platform
# This script installs dependencies and deploys the integrated collision detection server

set -e

echo "=== Setting up Collision Detection with Video Analysis ==="

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update -y

# Install Python and pip if not available
echo "🐍 Installing Python dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv

# Install system dependencies for OpenCV
echo "📹 Installing OpenCV system dependencies..."
sudo apt-get install -y \
    libopencv-dev \
    python3-opencv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0

# Create virtual environment
echo "🔧 Creating Python virtual environment..."
python3 -m venv collision_env
source collision_env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python packages
echo "📚 Installing Python packages..."
pip install \
    flask==2.3.3 \
    flask-socketio==5.3.6 \
    flask-cors==4.0.0 \
    eventlet==0.33.3 \
    python-dotenv==1.0.0 \
    opencv-python==4.8.1.78 \
    numpy==1.24.3 \
    ultralytics==8.0.196 \
    torch==2.0.1 \
    torchvision==0.15.2 \
    Pillow==10.0.1

# Download YOLO model
echo "🤖 Downloading YOLO model..."
python3 -c "
from ultralytics import YOLO
import os
model = YOLO('yolov8n.pt')
print('YOLO model downloaded successfully')
"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p /tmp/collision_uploads
mkdir -p /tmp/collision_uploads/processed
mkdir -p /home/$(whoami)/collision_logs

# Copy the collision detection server
echo "🚀 Setting up collision detection server..."
cp scripts/gcp-collision-integrated-server.py /home/$(whoami)/collision_server.py

# Create environment file
echo "⚙️ Creating environment configuration..."
cat > /home/$(whoami)/.env << EOF
# Collision Detection Server Configuration
HOST=0.0.0.0
PORT=5000
SECRET_KEY=collision-detection-secret-$(date +%s)
UPLOAD_FOLDER=/tmp/collision_uploads
DEBUG=False
ENVIRONMENT=production
EOF

# Create systemd service
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/collision-detection.service > /dev/null << EOF
[Unit]
Description=Collision Detection Server with Video Analysis
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=/home/$(whoami)
Environment=PATH=/home/$(whoami)/collision_env/bin
ExecStart=/home/$(whoami)/collision_env/bin/python collision_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=collision-detection

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
echo "🚀 Starting collision detection service..."
sudo systemctl daemon-reload
sudo systemctl enable collision-detection
sudo systemctl start collision-detection

# Wait for service to start
sleep 5

# Check service status
echo "📊 Checking service status..."
sudo systemctl status collision-detection --no-pager

# Test the server
echo "🧪 Testing server..."
sleep 2
curl -s http://localhost:5000/api/health | python3 -m json.tool || echo "Server not responding yet, check logs"

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 5000/tcp
echo "Firewall rule added for port 5000"

# Create simple test script
echo "📝 Creating test script..."
cat > /home/$(whoami)/test_collision_server.py << 'EOF'
#!/usr/bin/env python3
import requests
import json

def test_server():
    try:
        # Test health endpoint
        response = requests.get('http://localhost:5000/api/health')
        if response.status_code == 200:
            data = response.json()
            print("✅ Server is running!")
            print(f"Status: {data['status']}")
            print(f"Version: {data['version']}")
            print(f"Features: {', '.join(data['features'])}")
            return True
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return False

if __name__ == "__main__":
    test_server()
EOF

chmod +x /home/$(whoami)/test_collision_server.py

echo ""
echo "=== Collision Detection Setup Complete! ==="
echo ""
echo "🎉 Your collision detection server is now running!"
echo ""
echo "📍 Access your server at:"
echo "   http://$(curl -s ifconfig.me):5000"
echo "   http://localhost:5000 (local)"
echo ""
echo "🔧 Useful commands:"
echo "   sudo systemctl status collision-detection    # Check status"
echo "   sudo systemctl restart collision-detection   # Restart server"
echo "   sudo journalctl -u collision-detection -f    # View logs"
echo "   python3 test_collision_server.py             # Test server"
echo ""
echo "📁 Upload folder: /tmp/collision_uploads"
echo "📁 Processed videos: /tmp/collision_uploads/processed"
echo ""
echo "✨ Features available:"
echo "   • Video upload with drag & drop"
echo "   • Real-time collision detection"
echo "   • Bounding box visualization"
echo "   • YOLO object detection"
echo "   • Side-by-side video comparison"
echo ""
echo "🚀 Ready to analyze videos for collision detection!"