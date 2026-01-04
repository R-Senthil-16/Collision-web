#!/bin/bash

# Fix Collision Detection Server
# This script fixes the current server issues and deploys a working version

echo "🔧 Fixing Collision Detection Server..."

# Stop the current service
echo "⏹️ Stopping current service..."
sudo systemctl stop collision-detection 2>/dev/null || true

# Kill any processes using port 5000
echo "🔪 Killing processes on port 5000..."
sudo lsof -ti:5000 | xargs sudo kill -9 2>/dev/null || true

# Install missing dependencies
echo "📦 Installing missing dependencies..."
sudo apt-get update -q
sudo apt-get install -y python3-opencv libgl1-mesa-glx libglib2.0-0

# Install Python packages
echo "🐍 Installing Python packages..."
pip3 install --upgrade pip
pip3 install flask flask-cors opencv-python numpy

# Try to install YOLO (optional)
echo "🤖 Installing YOLO (optional)..."
pip3 install ultralytics torch torchvision --quiet || echo "⚠️ YOLO installation failed - will use simulation mode"

# Create directories
echo "📁 Creating directories..."
sudo mkdir -p /tmp/collision_uploads/processed
sudo chown $(whoami):$(whoami) /tmp/collision_uploads -R

# Copy the fixed server
echo "📋 Deploying fixed server..."
cp scripts/gcp-collision-simple-fix.py /home/$(whoami)/collision_server.py

# Create a simple systemd service
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/collision-detection.service > /dev/null << EOF
[Unit]
Description=Collision Detection Server
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=/home/$(whoami)
ExecStart=/usr/bin/python3 collision_server.py
Restart=always
RestartSec=5
Environment=HOST=0.0.0.0
Environment=PORT=5000

[Install]
WantedBy=multi-user.target
EOF

# Reload and start service
echo "🚀 Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable collision-detection
sudo systemctl start collision-detection

# Wait for service to start
sleep 3

# Check service status
echo "📊 Checking service status..."
sudo systemctl status collision-detection --no-pager --lines=10

# Test the server
echo "🧪 Testing server..."
sleep 2
if curl -s http://localhost:5000/api/health > /dev/null; then
    echo "✅ Server is responding!"
    curl -s http://localhost:5000/api/health | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" 2>/dev/null || echo "Server running but JSON parsing failed"
else
    echo "❌ Server not responding"
    echo "📋 Recent logs:"
    sudo journalctl -u collision-detection -n 20 --no-pager
fi

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 5000/tcp 2>/dev/null || echo "UFW not available or already configured"

echo ""
echo "=== Fix Complete! ==="
echo ""
echo "🌐 Access your server at:"
echo "   http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR-VM-IP'):5000"
echo ""
echo "🔧 Useful commands:"
echo "   sudo systemctl status collision-detection"
echo "   sudo journalctl -u collision-detection -f"
echo "   curl http://localhost:5000/api/health"
echo ""
echo "✨ The server now includes:"
echo "   • Simplified, stable Flask server"
echo "   • Video upload with collision detection"
echo "   • YOLO integration (with fallback simulation)"
echo "   • Bounding box visualization"
echo "   • Error handling and logging"