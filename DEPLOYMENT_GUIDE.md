# Collision Detection System - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying and configuring the Collision Detection System across all three components:
- **Raspberry Pi Server** (Python-based backend)
- **Web Interface** (JavaScript frontend)
- **ESP8266 Devices** (C++ firmware)

## System Requirements

### Raspberry Pi Server
- **Hardware**: Raspberry Pi 4 (4GB RAM recommended) or compatible Linux system
- **OS**: Raspberry Pi OS (Bullseye) or Ubuntu 20.04+
- **Python**: 3.8 or higher
- **Storage**: 32GB SD card minimum (64GB recommended)
- **Network**: WiFi or Ethernet connection
- **Camera**: USB camera or Raspberry Pi Camera Module (optional)

### Web Interface
- **Browser**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Network**: Access to Raspberry Pi server
- **Resolution**: 1024x768 minimum (1920x1080 recommended)

### ESP8266 Devices
- **Hardware**: ESP8266 NodeMCU, Wemos D1 Mini, or compatible
- **Memory**: 4MB flash minimum
- **Network**: 2.4GHz WiFi network
- **Power**: 3.3V power supply or USB
- **Peripherals**: LEDs, servos, relays as needed

## Pre-Installation Setup

### 1. Raspberry Pi Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-pip python3-venv git cmake build-essential
sudo apt install -y libopencv-dev python3-opencv
sudo apt install -y libhdf5-dev libatlas-base-dev
sudo apt install -y nginx supervisor

# Enable camera (if using Pi Camera)
sudo raspi-config
# Navigate to Interface Options > Camera > Enable

# Increase GPU memory split for camera processing
echo "gpu_mem=128" | sudo tee -a /boot/config.txt

# Reboot to apply changes
sudo reboot
```

### 2. Network Configuration

```bash
# Configure static IP (optional but recommended)
sudo nano /etc/dhcpcd.conf

# Add the following lines:
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8

# Restart networking
sudo systemctl restart dhcpcd
```

## Installation Instructions

### 1. Raspberry Pi Server Installation

```bash
# Clone the repository
git clone <repository-url>
cd collision-detection-system

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
cd raspberry-pi
pip install -r requirements.txt
pip install -e .

# Create necessary directories
sudo mkdir -p /var/log/collision-detection
sudo mkdir -p /var/lib/collision-detection/uploads
sudo mkdir -p /var/lib/collision-detection/models

# Set permissions
sudo chown -R pi:pi /var/log/collision-detection
sudo chown -R pi:pi /var/lib/collision-detection
```

### 2. Web Interface Setup

```bash
# Install Node.js and npm (if not already installed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Navigate to web directory
cd ../web

# Install dependencies
npm install

# Build production assets (optional)
npm run build

# Configure nginx for web serving
sudo cp deployment/nginx.conf /etc/nginx/sites-available/collision-detection
sudo ln -s /etc/nginx/sites-available/collision-detection /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 3. ESP8266 Firmware Installation

```bash
# Install PlatformIO (if not already installed)
pip install platformio

# Navigate to ESP8266 directory
cd ../esp8266-devices

# Configure WiFi credentials
cp include/config.h.example include/config.h
nano include/config.h

# Update the following in config.h:
#define WIFI_SSID "YourWiFiNetwork"
#define WIFI_PASSWORD "YourWiFiPassword"
#define RASPBERRY_PI_IP "192.168.1.100"

# Build and upload firmware
pio run --target upload

# Monitor serial output (optional)
pio device monitor
```

## Configuration

### 1. Environment Variables

Create environment configuration files:

```bash
# Raspberry Pi server environment
cd raspberry-pi
cp .env.example .env
nano .env
```

Configure the following variables in `.env`:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=5000
DEBUG=False
SECRET_KEY=your-secret-key-here

# File Storage
UPLOAD_FOLDER=/var/lib/collision-detection/uploads
LOG_DIRECTORY=/var/log/collision-detection
MAX_CONTENT_LENGTH=524288000  # 500MB

# Hardware Configuration
DISCOVERY_PORT=8888
COMMAND_PORT=8889
STATUS_PORT=8890
NETWORK_TIMEOUT=5.0
DISCOVERY_INTERVAL=30.0

# Computer Vision
MODEL_PATH=/var/lib/collision-detection/models
CONFIDENCE_THRESHOLD=0.5
COLLISION_THRESHOLD=0.7

# Performance
RESOURCE_CONFIG=production
ENABLE_MONITORING=True
PERFORMANCE_LOGGING=True
```

### 2. System Service Configuration

Create systemd service for automatic startup:

```bash
sudo nano /etc/systemd/system/collision-detection.service
```

Add the following content:

```ini
[Unit]
Description=Collision Detection Server
After=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/collision-detection-system/raspberry-pi
Environment=PATH=/home/pi/collision-detection-system/venv/bin
ExecStart=/home/pi/collision-detection-system/venv/bin/python -m collision_server.main
Restart=always
RestartSec=10

# Environment file
EnvironmentFile=/home/pi/collision-detection-system/raspberry-pi/.env

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=collision-detection

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable collision-detection
sudo systemctl start collision-detection

# Check service status
sudo systemctl status collision-detection

# View logs
sudo journalctl -u collision-detection -f
```

### 3. Nginx Configuration

Create nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/collision-detection
```

Add the following content:

```nginx
server {
    listen 80;
    server_name localhost;

    # Web interface static files
    location / {
        root /home/pi/collision-detection-system/web;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API proxy to Flask server
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for video processing
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket endpoint
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # File upload size limit
    client_max_body_size 500M;

    # Logging
    access_log /var/log/nginx/collision-detection.access.log;
    error_log /var/log/nginx/collision-detection.error.log;
}
```

### 4. Log Rotation Configuration

Configure log rotation to prevent disk space issues:

```bash
sudo nano /etc/logrotate.d/collision-detection
```

Add the following content:

```
/var/log/collision-detection/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 pi pi
    postrotate
        systemctl reload collision-detection
    endscript
}
```

## Device Configuration

### 1. ESP8266 Device Setup

Each ESP8266 device needs to be configured with:

1. **WiFi Credentials**: Network SSID and password
2. **Raspberry Pi IP**: IP address of the server
3. **Device ID**: Unique identifier for the device
4. **Hardware Configuration**: Pin assignments for LEDs, servos, relays

Example configuration in `include/config.h`:

```cpp
// WiFi Configuration
#define WIFI_SSID "YourNetwork"
#define WIFI_PASSWORD "YourPassword"
#define RASPBERRY_PI_IP "192.168.1.100"

// Device Configuration
#define DEVICE_ID_PREFIX "ESP8266_"
#define SERVER_PORT 80

// Hardware Pin Assignments
#define LED_RED_PIN D1
#define LED_GREEN_PIN D2
#define LED_BLUE_PIN D3
#define SERVO_PIN D4
#define RELAY_PIN D5
#define STATUS_LED_PIN D0

// Network Configuration
#define HEARTBEAT_INTERVAL_MS 30000
#define STATUS_UPDATE_INTERVAL_MS 10000
#define WIFI_CONNECT_TIMEOUT_MS 30000
#define MAX_WIFI_RECONNECT_ATTEMPTS 5

// Performance Configuration
#define LOOP_DELAY_MS 100
#define JSON_BUFFER_SIZE 1024
```

### 2. Camera Configuration

For USB cameras, configure device permissions:

```bash
# Add user to video group
sudo usermod -a -G video pi

# Create udev rule for camera permissions
sudo nano /etc/udev/rules.d/99-camera.rules
```

Add the following content:

```
SUBSYSTEM=="video4linux", GROUP="video", MODE="0664"
KERNEL=="video[0-9]*", GROUP="video", MODE="0664"
```

Reload udev rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Testing and Validation

### 1. System Health Check

```bash
# Check all services
sudo systemctl status collision-detection
sudo systemctl status nginx

# Test API endpoints
curl http://localhost/api/health
curl http://localhost/api/system/health

# Check logs
sudo journalctl -u collision-detection --since "1 hour ago"
tail -f /var/log/collision-detection/system.log
```

### 2. Integration Testing

```bash
# Run integration tests
cd raspberry-pi
python -m pytest tests/ -v

# Run comprehensive integration tests
python ../comprehensive_integration_tests.py
```

### 3. Performance Testing

```bash
# Monitor system resources
htop
iotop
nethogs

# Check disk usage
df -h
du -sh /var/lib/collision-detection/*
du -sh /var/log/collision-detection/*

# Network connectivity test
ping 8.8.8.8
nmap -p 5000 localhost
```

## Monitoring and Maintenance

### 1. System Monitoring

The system includes built-in monitoring accessible via:
- Web interface: `http://raspberry-pi-ip/` → System Monitor tab
- API endpoints: `/api/system/health`, `/api/system/metrics`
- Log files: `/var/log/collision-detection/`

### 2. Regular Maintenance Tasks

```bash
# Weekly maintenance script
#!/bin/bash

# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean old log files
sudo find /var/log/collision-detection -name "*.log.*" -mtime +30 -delete

# Clean old uploaded videos
sudo find /var/lib/collision-detection/uploads -name "*.mp4" -mtime +7 -delete

# Check disk space
df -h | grep -E "(/$|/var)"

# Restart services if needed
sudo systemctl restart collision-detection
sudo systemctl restart nginx

# Check service health
curl -f http://localhost/api/health || echo "Health check failed"
```

### 3. Backup Procedures

```bash
# Backup configuration files
tar -czf collision-detection-config-$(date +%Y%m%d).tar.gz \
    /home/pi/collision-detection-system/raspberry-pi/.env \
    /home/pi/collision-detection-system/esp8266-devices/include/config.h \
    /etc/nginx/sites-available/collision-detection \
    /etc/systemd/system/collision-detection.service

# Backup logs (optional)
tar -czf collision-detection-logs-$(date +%Y%m%d).tar.gz \
    /var/log/collision-detection/

# Upload backups to remote storage (configure as needed)
# rsync -av *.tar.gz user@backup-server:/backups/collision-detection/
```

## Troubleshooting

### Common Issues

1. **Server won't start**
   ```bash
   # Check Python environment
   source venv/bin/activate
   python -c "import collision_server; print('OK')"
   
   # Check dependencies
   pip check
   
   # Check permissions
   ls -la /var/lib/collision-detection/
   ls -la /var/log/collision-detection/
   ```

2. **Camera not detected**
   ```bash
   # List video devices
   ls -la /dev/video*
   
   # Test camera with OpenCV
   python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera failed')"
   ```

3. **ESP8266 connection issues**
   ```bash
   # Check network connectivity
   ping esp8266-device-ip
   
   # Check device logs via serial monitor
   pio device monitor
   
   # Verify WiFi credentials in config.h
   ```

4. **Web interface not loading**
   ```bash
   # Check nginx status
   sudo systemctl status nginx
   
   # Check nginx configuration
   sudo nginx -t
   
   # Check file permissions
   ls -la /home/pi/collision-detection-system/web/
   ```

### Performance Optimization

1. **Raspberry Pi Performance**
   ```bash
   # Increase GPU memory for camera processing
   echo "gpu_mem=128" | sudo tee -a /boot/config.txt
   
   # Enable hardware acceleration
   echo "dtoverlay=vc4-kms-v3d" | sudo tee -a /boot/config.txt
   
   # Optimize SD card performance
   echo "dtparam=sd_overclock=100" | sudo tee -a /boot/config.txt
   ```

2. **Network Optimization**
   ```bash
   # Increase network buffer sizes
   echo "net.core.rmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
   echo "net.core.wmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
   ```

## Security Considerations

### 1. Network Security

```bash
# Configure firewall
sudo ufw enable
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS (if using SSL)
sudo ufw allow 5000/tcp # Flask (if direct access needed)

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

### 2. SSL/HTTPS Configuration (Optional)

```bash
# Install certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate (requires domain name)
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Access Control

```bash
# Change default passwords
sudo passwd pi

# Disable SSH password authentication (use keys)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PubkeyAuthentication yes

sudo systemctl restart ssh
```

## Scaling and Production Deployment

### 1. Load Balancing (Multiple Raspberry Pi)

```nginx
upstream collision_backend {
    server 192.168.1.100:5000;
    server 192.168.1.101:5000;
    server 192.168.1.102:5000;
}

server {
    location /api/ {
        proxy_pass http://collision_backend;
        # ... other proxy settings
    }
}
```

### 2. Database Integration (Optional)

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Configure database connection in .env
DATABASE_URL=postgresql://user:password@localhost/collision_detection
```

### 3. Container Deployment (Docker)

```dockerfile
# Dockerfile for Raspberry Pi server
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "-m", "collision_server.main"]
```

This deployment guide provides comprehensive instructions for setting up the collision detection system in various environments, from development to production deployment.