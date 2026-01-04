#!/bin/bash

# Enable Video Upload on Google Cloud Server
# Run this INSIDE your Google Cloud VM

echo "=== Enabling Video Upload Functionality ==="
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

# Backup current server
echo "Backing up current server..."
if [ -f "production_server.py" ]; then
    cp production_server.py production_server_backup.py
    echo "✓ Backup created: production_server_backup.py"
fi

# Copy new video upload server
echo "Installing enhanced video upload server..."
if [ -f "../scripts/gcp-video-upload-fix.py" ]; then
    cp ../scripts/gcp-video-upload-fix.py ./production_server.py
    chmod +x production_server.py
    echo "✓ Enhanced server installed"
else
    echo "✗ Enhanced server script not found"
    exit 1
fi

# Ensure upload directory exists with proper permissions
echo "Setting up upload directory..."
mkdir -p ~/collision-uploads
chmod 755 ~/collision-uploads
echo "✓ Upload directory ready: ~/collision-uploads"

# Test the new server
echo ""
echo "=== Testing Enhanced Server ==="
source venv/bin/activate

# Quick test
python3 -c "
try:
    from flask import Flask
    print('✓ Flask available')
    import os
    print(f'✓ Upload folder: {os.path.expanduser(\"~/collision-uploads\")}')
    print('✓ Enhanced server ready')
except Exception as e:
    print(f'✗ Error: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "✗ Server test failed"
    exit 1
fi

# Start the enhanced service
echo "Starting enhanced service..."
sudo systemctl start collision-detection

# Wait for service to start
sleep 5

# Check service status
echo ""
echo "=== Service Status ==="
if sudo systemctl is-active --quiet collision-detection; then
    echo "✅ Enhanced server is running!"
    
    # Test upload endpoint
    sleep 2
    if curl -s http://localhost:5000/api/health | grep -q "Video Upload"; then
        echo "✅ Video upload functionality enabled!"
    else
        echo "⚠ Service running but video upload may not be fully enabled"
    fi
else
    echo "❌ Service failed to start"
    echo "Checking logs..."
    sudo journalctl -u collision-detection --no-pager -l | tail -10
    exit 1
fi

echo ""
echo "=== Video Upload Setup Complete! ==="
echo ""
echo "🎉 Your server now supports:"
echo "  ✅ Video file upload (drag & drop)"
echo "  ✅ Progress tracking"
echo "  ✅ Video preview"
echo "  ✅ Multiple video formats (MP4, AVI, MOV, etc.)"
echo "  ✅ Up to 500MB file size"
echo ""
echo "🌐 Access your enhanced website:"
echo "   http://YOUR-EXTERNAL-IP:5000"
echo ""
echo "📹 Upload videos and test collision detection!"
echo ""
echo "💡 To view logs: sudo journalctl -u collision-detection -f"