#!/bin/bash

# Simple Firewall Setup for Google Cloud
# Run this on your LOCAL COMPUTER (not inside the VM)

echo "=== Setting up Google Cloud Firewall ==="

# Create firewall rule for port 5000
echo "Creating firewall rule for port 5000..."
gcloud compute firewall-rules create allow-collision-port-5000 \
    --allow tcp:5000 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow collision detection server on port 5000"

# Add network tags to VM
echo "Adding network tags to VM..."
gcloud compute instances add-tags collision-detection-server \
    --tags http-server \
    --zone us-central1-a

# Get external IP
echo ""
echo "Getting your VM's external IP address..."
EXTERNAL_IP=$(gcloud compute instances describe collision-detection-server \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "=== Firewall Setup Complete ==="
echo ""
echo "Your VM External IP: $EXTERNAL_IP"
echo ""
echo "Test your deployment:"
echo "  Web Interface: http://$EXTERNAL_IP:5000"
echo "  API Health:    http://$EXTERNAL_IP:5000/api/health"
echo ""
echo "If you can't connect, wait 2-3 minutes for firewall rules to take effect."