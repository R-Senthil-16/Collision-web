#!/bin/bash

# Setup Collision Analysis with YOLO Integration
# Run this INSIDE your Google Cloud VM

echo "=== Setting up Collision Analysis with YOLO Integration ==="
echo ""

# Navigate to project directory
cd ~/Collision-web/raspberry-pi || {
    echo "Error: Could not find project directory"
    exit 1
}

echo "Working directory: $(pwd)"

# Stop current service
echo "Stopping current service..."
sudo systemctl stop collision-detection

# Activate virtual environment
source venv/bin/activate

# Install computer vision dependencies
echo "Installing computer vision dependencies..."
echo "This may take several minutes..."

# Install OpenCV and dependencies
pip install opencv-python==4.8.1.78
pip install numpy==1.24.3

# Install YOLO (ultralytics)
pip install ultralytics==8.0.196

# Install additional dependencies for video processing
pip install Pillow==10.0.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo "✓ Computer vision dependencies installed"

# Copy your collision detection code
echo "Setting up collision detection integration..."

# Copy the realtime collision detection code to the project
if [ -f "../realtime_collision_detection.py" ]; then
    cp ../realtime_collision_detection.py ./collision_detection_core.py
    echo "✓ Collision detection core copied"
else
    echo "⚠ realtime_collision_detection.py not found, using integrated version"
fi

# Download YOLO model if not present
echo "Downloading YOLO model..."
if [ ! -f "yolov8n.pt" ]; then
    python3 -c "
from ultralytics import YOLO
print('Downloading YOLOv8 nano model...')
model = YOLO('yolov8n.pt')
print('✓ YOLO model downloaded successfully')
"
else
    echo "✓ YOLO model already exists"
fi

# Backup current server and install new one
echo "Installing enhanced video analysis server..."
if [ -f "production_server.py" ]; then
    cp production_server.py production_server_backup.py
    echo "✓ Backup created: production_server_backup.py"
fi

# Copy new video analysis server
cp ../scripts/gcp-video-analysis-server.py ./production_server.py
chmod +x production_server.py
echo "✓ Enhanced video analysis server installed"

# Test the installation
echo ""
echo "=== Testing Installation ==="

python3 -c "
import sys
print('Testing dependencies...')

try:
    import cv2
    print(f'✓ OpenCV: {cv2.__version__}')
except ImportError as e:
    print(f'✗ OpenCV: {e}')
    sys.exit(1)

try:
    import numpy as np
    print(f'✓ NumPy: {np.__version__}')
except ImportError as e:
    print(f'✗ NumPy: {e}')
    sys.exit(1)

try:
    from ultralytics import YOLO
    print('✓ Ultralytics YOLO available')
    
    # Test model loading
    import os
    if os.path.exists('yolov8n.pt'):
        model = YOLO('yolov8n.pt')
        print('✓ YOLO model loads successfully')
    else:
        print('⚠ YOLO model file not found')
        
except ImportError as e:
    print(f'✗ Ultralytics: {e}')
    sys.exit(1)

print('✅ All dependencies working correctly!')
"

if [ $? -ne 0 ]; then
    echo "❌ Dependency test failed"
    exit 1
fi

# Start the enhanced service
echo ""
echo "Starting enhanced collision analysis service..."
sudo systemctl start collision-detection

# Wait for service to start
sleep 8

# Check service status
echo ""
echo "=== Service Status ==="
if sudo systemctl is-active --quiet collision-detection; then
    echo "✅ Enhanced collision analysis server is running!"
    
    # Test the enhanced endpoints
    sleep 3
    if curl -s http://localhost:5000/api/health | grep -q "YOLO"; then
        echo "✅ YOLO analysis functionality enabled!"
    else
        echo "⚠ Service running but YOLO analysis may not be fully enabled"
    fi
else
    echo "❌ Service failed to start"
    echo "Checking logs..."
    sudo journalctl -u collision-detection --no-pager -l | tail -15
    exit 1
fi

echo ""
echo "=== Collision Analysis Setup Complete! ==="
echo ""
echo "🎉 Your server now includes:"
echo "  ✅ YOLO v8 object detection"
echo "  ✅ Real-time collision detection"
echo "  ✅ Vehicle classification (car, truck, motorcycle, etc.)"
echo "  ✅ Risk assessment and scoring"
echo "  ✅ Frame-by-frame analysis"
echo "  ✅ WebSocket real-time updates"
echo "  ✅ Professional analysis interface"
echo ""
echo "🌐 Access your enhanced collision detection system:"
echo "   http://YOUR-EXTERNAL-IP:5000"
echo ""
echo "📹 Upload a video and click 'Analyze for Collisions' to see:"
echo "   • Vehicle detection and tracking"
echo "   • Collision risk assessment"
echo "   • Detailed analysis statistics"
echo "   • Risk level classification"
echo ""
echo "💡 Your collision detection code is now integrated!"
echo "💡 To view logs: sudo journalctl -u collision-detection -f"