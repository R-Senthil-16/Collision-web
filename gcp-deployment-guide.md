# Google Cloud Platform Deployment Guide

## Prerequisites
- Google Cloud account with billing enabled
- gcloud CLI installed (optional, can use web console)

## Option 1: Compute Engine VM (Recommended)

### Step 1: Create VM Instance

**Via Web Console:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to Compute Engine > VM instances
3. Click "Create Instance"
4. Configure:
   - **Name:** collision-detection-server
   - **Region:** us-central1 (or closest to you)
   - **Machine type:** e2-standard-2 (2 vCPU, 8GB RAM) - $60/month
   - **Boot disk:** Ubuntu 20.04 LTS, 20GB SSD
   - **Firewall:** Allow HTTP and HTTPS traffic

**Via gcloud CLI:**
```bash
gcloud compute instances create collision-detection-server \
    --zone=us-central1-a \
    --machine-type=e2-standard-2 \
    --subnet=default \
    --network-tier=PREMIUM \
    --maintenance-policy=MIGRATE \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --boot-disk-type=pd-ssd \
    --tags=http-server,https-server
```

### Step 2: Configure Firewall Rules

```bash
# Allow port 5000 for Flask app
gcloud compute firewall-rules create allow-collision-detection \
    --allow tcp:5000 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow collision detection server"

# Allow port 80 for web interface
gcloud compute firewall-rules create allow-http \
    --allow tcp:80 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow HTTP traffic"
```

### Step 3: SSH into VM and Setup

```bash
# SSH into your VM
gcloud compute ssh collision-detection-server --zone=us-central1-a

# Or use the web SSH from console
```

### Step 4: Install Dependencies on VM

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3-pip python3-venv git nginx
sudo apt install -y python3-opencv libopencv-dev
sudo apt install -y build-essential cmake pkg-config
sudo apt install -y libjpeg-dev libtiff5-dev libpng-dev
sudo apt install -y libavcodec-dev libavformat-dev libswscale-dev
sudo apt install -y libatlas-base-dev gfortran

# Clone your repository
git clone https://github.com/yourusername/collision-detection-system.git
cd collision-detection-system

# Setup Python environment
cd raspberry-pi
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure Environment

```bash
# Create environment file
cp .env.example .env
nano .env
```

Update `.env` with:
```bash
HOST=0.0.0.0
PORT=5000
DEBUG=False
SECRET_KEY=your-secure-secret-key-here
UPLOAD_FOLDER=/home/$(whoami)/collision-uploads
LOG_DIRECTORY=/home/$(whoami)/collision-logs
```

```bash
# Create directories
mkdir -p ~/collision-uploads ~/collision-logs
```

### Step 6: Setup Nginx (Optional)

```bash
# Configure nginx
sudo nano /etc/nginx/sites-available/collision-detection
```

Add nginx configuration:
```nginx
server {
    listen 80;
    server_name _;

    location / {
        root /home/$(whoami)/collision-detection-system/web;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        client_max_body_size 500M;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/collision-detection /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 7: Create Systemd Service

```bash
sudo nano /etc/systemd/system/collision-detection.service
```

Add service configuration:
```ini
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
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable collision-detection
sudo systemctl start collision-detection

# Check status
sudo systemctl status collision-detection
```

### Step 8: Get External IP and Test

```bash
# Get your VM's external IP
gcloud compute instances describe collision-detection-server \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

Access your system:
- **Web Interface:** `http://YOUR-EXTERNAL-IP/`
- **API:** `http://YOUR-EXTERNAL-IP/api/health`

## Option 2: Cloud Run (Serverless)

### Step 1: Build and Deploy Container

```bash
# Build container image
gcloud builds submit --tag gcr.io/YOUR-PROJECT-ID/collision-detection

# Deploy to Cloud Run
gcloud run deploy collision-detection \
    --image gcr.io/YOUR-PROJECT-ID/collision-detection \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 10
```

## Option 3: App Engine (Fully Managed)

### Step 1: Create app.yaml

```yaml
runtime: python39
service: default

env_variables:
  DEBUG: "False"
  UPLOAD_FOLDER: "/tmp/uploads"
  LOG_DIRECTORY: "/tmp/logs"

automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.6

resources:
  cpu: 2
  memory_gb: 4
  disk_size_gb: 10
```

### Step 2: Deploy

```bash
cd raspberry-pi
gcloud app deploy
```

## Cost Estimates

### Compute Engine VM:
- **e2-standard-2:** ~$60/month (always on)
- **e2-medium:** ~$30/month (2GB RAM, good for testing)
- **Preemptible instances:** ~$18/month (can be stopped by Google)

### Cloud Run:
- **Pay per request:** $0 when not in use
- **Active usage:** ~$10-30/month depending on traffic

### App Engine:
- **Standard environment:** ~$50-100/month
- **Automatic scaling included**

## Benefits of Google Cloud vs Raspberry Pi

✅ **More powerful:** 2-8 CPU cores vs Pi's 4 ARM cores
✅ **More RAM:** 8GB+ vs Pi's 4GB max
✅ **Better networking:** Gigabit internet vs home WiFi
✅ **No dependency issues:** Standard Ubuntu environment
✅ **Automatic backups:** Built-in snapshot capabilities
✅ **Global access:** Access from anywhere
✅ **Scalability:** Can upgrade resources instantly
✅ **Reliability:** 99.9% uptime SLA
✅ **Security:** Google's infrastructure security

## Quick Start Commands

```bash
# Create VM and setup in one go
gcloud compute instances create collision-detection-server \
    --zone=us-central1-a \
    --machine-type=e2-standard-2 \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --tags=http-server,https-server \
    --metadata=startup-script='#!/bin/bash
    apt update && apt install -y python3-pip python3-venv git nginx python3-opencv
    git clone https://github.com/yourusername/collision-detection-system.git /opt/collision-detection
    cd /opt/collision-detection/raspberry-pi
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    '
```