#!/bin/bash

# Quick deployment script for collision detection server
# Run this on your Google Cloud VM

echo "🚀 Deploying Collision Detection Server..."

# Stop existing server if running
sudo systemctl stop collision-detection 2>/dev/null || true

# Copy the new server file
cp scripts/gcp-collision-integrated-server.py /home/$(whoami)/collision_server.py

# Restart the service
sudo systemctl start collision-detection

# Check status
sleep 3
sudo systemctl status collision-detection --no-pager

echo ""
echo "✅ Collision detection server deployed!"
echo "🌐 Access at: http://$(curl -s ifconfig.me):5000"