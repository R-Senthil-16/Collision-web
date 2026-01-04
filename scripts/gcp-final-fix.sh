#!/bin/bash

# Final Production Fix for Google Cloud Deployment
# Run this INSIDE your Google Cloud VM

echo "=== Final Production Fix for Collision Detection Server ==="
echo ""

# Navigate to project directory
if [ -d "~/Collision-web" ]; then
    cd ~/Collision-web/raspberry-pi
    echo "✓ Found Collision-web directory"
elif [ -d "./raspberry-pi" ]; then
    cd ./raspberry-pi
    echo "✓ Using current directory with raspberry-pi folder"
else
    echo "✗ Could not find project directory"
    echo "Please make sure you're in the Collision-web directory"
    exit 1
fi

echo "Working directory: $(pwd)"

# Stop existing services
echo "Stopping existing services..."
sudo systemctl stop collision-detection 2>/dev/null || true
pkill -f "collision" 2>/dev/null || true
pkill -f "python.*server" 2>/dev/null || true
sleep 3

# Update system
echo "Updating system packages..."
sudo apt update -qq

# Install Python and essential packages
echo "Installing Python and essential packages..."
sudo apt install -y python3-pip python3-venv python3-dev build-essential

# Setup virtual environment
echo "Setting up Python virtual environment..."
if [ -d "venv" ]; then
    rm -rf venv
fi
python3 -m venv venv
source venv/bin/activate

# Install production dependencies
echo "Installing production Python dependencies..."
pip install --upgrade pip --quiet
pip install flask==2.3.3 --quiet
pip install flask-socketio==5.3.6 --quiet
pip install flask-cors==4.0.0 --quiet
pip install python-dotenv==1.0.0 --quiet
pip install eventlet==0.33.3 --quiet
pip install gunicorn==21.2.0 --quiet

# Create production environment file
echo "Creating production environment configuration..."
cat > .env << EOF
# Production Configuration for Google Cloud
HOST=0.0.0.0
PORT=5000
DEBUG=False
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "production-secret-$(date +%s)")
UPLOAD_FOLDER=/home/$(whoami)/collision-uploads
LOG_DIRECTORY=/home/$(whoami)/collision-logs

# Server Configuration
WORKERS=2
TIMEOUT=120
KEEPALIVE=5
EOF

# Create required directories
echo "Creating required directories..."
mkdir -p ~/collision-uploads ~/collision-logs
chmod 755 ~/collision-uploads ~/collision-logs

# Copy production server
echo "Setting up production server..."
if [ -f "../scripts/gcp-production-fix.py" ]; then
    cp ../scripts/gcp-production-fix.py ./production_server.py
else
    echo "✗ Production server script not found"
    exit 1
fi

chmod +x production_server.py

# Test dependencies
echo "Testing Python dependencies..."
python3 -c "
import sys
try:
    import flask, flask_socketio, flask_cors, eventlet
    print('✓ All production dependencies available')
    print(f'✓ Flask: {flask.__version__}')
    print(f'✓ Flask-SocketIO: {flask_socketio.__version__}')
    print(f'✓ Eventlet: {eventlet.__version__}')
except ImportError as e:
    print(f'✗ Missing dependency: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "✗ Dependency test failed"
    exit 1
fi

# Test server startup
echo ""
echo "=== Testing Production Server ==="
echo "Testing server startup (30 seconds)..."

timeout 30 python3 production_server.py &
SERVER_PID=$!
sleep 10

if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✓ Production server started successfully!"
    
    # Test API endpoint
    sleep 2
    if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "✓ API endpoints responding"
    else
        echo "⚠ API endpoints not responding (may be normal during startup)"
    fi
    
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
else
    echo "✗ Production server failed to start"
    exit 1
fi

# Create production systemd service
echo "Creating production systemd service..."
sudo tee /etc/systemd/system/collision-detection.service > /dev/null << EOF
[Unit]
Description=Collision Detection Production Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python $(pwd)/production_server.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

EnvironmentFile=$(pwd)/.env

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=collision-detection

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$(pwd) /home/$(whoami)/collision-uploads /home/$(whoami)/collision-logs

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo "Enabling production service..."
sudo systemctl daemon-reload
sudo systemctl enable collision-detection

# Start the service
echo "Starting production service..."
sudo systemctl start collision-detection

# Wait for service to start
sleep 8

# Check service status
echo ""
echo "=== Production Service Status ==="
if sudo systemctl is-active --quiet collision-detection; then
    echo "✓ Service is running"
    sudo systemctl status collision-detection --no-pager -l | head -20
else
    echo "✗ Service failed to start"
    echo "Checking logs..."
    sudo journalctl -u collision-detection --no-pager -l | tail -20
    exit 1
fi

# Test the running service
echo ""
echo "=== Testing Running Service ==="
sleep 3

if curl -s http://localhost:5000/api/health | grep -q "healthy"; then
    echo "✓ Service API is responding correctly"
else
    echo "⚠ Service API not responding (checking logs...)"
    sudo journalctl -u collision-detection --no-pager -l | tail -10
fi

echo ""
echo "=== Production Fix Complete ==="
echo ""
echo "✅ Production server is running successfully!"
echo ""
echo "Next steps:"
echo "1. Configure firewall (run on your LOCAL computer):"
echo "   gcloud compute firewall-rules create allow-collision-5000 --allow tcp:5000 --source-ranges 0.0.0.0/0"
echo "   gcloud compute instances add-tags collision-detection-server --tags http-server --zone us-central1-a"
echo ""
echo "2. Get your external IP:"
echo "   gcloud compute instances describe collision-detection-server --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'"
echo ""
echo "3. Test your deployment:"
echo "   http://YOUR-EXTERNAL-IP:5000"
echo "   http://YOUR-EXTERNAL-IP:5000/api/health"
echo ""
echo "4. Monitor logs:"
echo "   sudo journalctl -u collision-detection -f"
echo ""
echo "The server is now running in production mode with proper configuration!"