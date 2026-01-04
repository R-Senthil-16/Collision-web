#!/bin/bash
# Google Cloud Platform Setup Script for Collision Detection System

echo "🚀 Setting up Collision Detection System on Google Cloud..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv git nginx
sudo apt install -y python3-opencv libopencv-dev
sudo apt install -y build-essential cmake pkg-config
sudo apt install -y libjpeg-dev libtiff5-dev libpng-dev
sudo apt install -y libavcodec-dev libavformat-dev libswscale-dev

echo "📦 Dependencies installed successfully"

# Clone repository (replace with your actual repo)
if [ ! -d "collision-detection-system" ]; then
    echo "📥 Cloning repository..."
    git clone https://github.com/yourusername/collision-detection-system.git
fi

cd collision-detection-system/raspberry-pi

# Setup Python environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip setuptools wheel
pip install flask==2.3.3
pip install flask-socketio==5.3.6
pip install flask-cors==4.0.0
pip install python-dotenv==1.0.0
pip install opencv-python-headless==4.8.1.78
pip install numpy==1.24.3
pip install requests==2.31.0
pip install psutil==5.9.5

echo "📁 Creating directories..."
mkdir -p ~/collision-uploads ~/collision-logs

# Create environment file
echo "⚙️ Creating environment configuration..."
cat > .env << EOF
HOST=0.0.0.0
PORT=5000
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
UPLOAD_FOLDER=/home/$(whoami)/collision-uploads
LOG_DIRECTORY=/home/$(whoami)/collision-logs
MAX_CONTENT_LENGTH=524288000
DISCOVERY_PORT=8888
COMMAND_PORT=8889
STATUS_PORT=8890
NETWORK_TIMEOUT=5.0
DISCOVERY_INTERVAL=30.0
CONFIDENCE_THRESHOLD=0.5
COLLISION_THRESHOLD=0.7
RESOURCE_CONFIG=production
ENABLE_MONITORING=True
PERFORMANCE_LOGGING=True
EOF

# Create systemd service
echo "🔧 Creating system service..."
sudo tee /etc/systemd/system/collision-detection.service > /dev/null << EOF
[Unit]
Description=Collision Detection Server
After=network.target

[Service]
Type=simple
User=$(whoami)
Group=$(whoami)
WorkingDirectory=/home/$(whoami)/collision-detection-system/raspberry-pi
Environment=PATH=/home/$(whoami)/collision-detection-system/raspberry-pi/venv/bin
ExecStart=/home/$(whoami)/collision-detection-system/raspberry-pi/venv/bin/python -m collision_server.main
Restart=always
RestartSec=10

EnvironmentFile=/home/$(whoami)/collision-detection-system/raspberry-pi/.env

StandardOutput=journal
StandardError=journal
SyslogIdentifier=collision-detection

[Install]
WantedBy=multi-user.target
EOF

# Configure nginx
echo "🌐 Configuring web server..."
sudo tee /etc/nginx/sites-available/collision-detection > /dev/null << EOF
server {
    listen 80;
    server_name _;

    # Web interface
    location / {
        root /home/$(whoami)/collision-detection-system/web;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        client_max_body_size 500M;
    }

    # WebSocket
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/collision-detection /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t

# Start services
echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable collision-detection
sudo systemctl start collision-detection
sudo systemctl restart nginx
sudo systemctl enable nginx

# Get external IP
EXTERNAL_IP=$(curl -s http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip -H "Metadata-Flavor: Google")

echo ""
echo "🎉 Setup complete!"
echo ""
echo "🌐 Access your collision detection system:"
echo "   Web Interface: http://$EXTERNAL_IP/"
echo "   API Health:    http://$EXTERNAL_IP/api/health"
echo ""
echo "📊 Check service status:"
echo "   sudo systemctl status collision-detection"
echo "   sudo journalctl -u collision-detection -f"
echo ""
echo "💡 To update your system:"
echo "   cd ~/collision-detection-system && git pull"
echo "   sudo systemctl restart collision-detection"