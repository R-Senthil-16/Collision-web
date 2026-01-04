#!/bin/bash

# Google Cloud Firewall Setup Script
# Run this on your LOCAL COMPUTER (not inside the VM)

echo "Setting up Google Cloud firewall rules..."

# Create firewall rule for collision detection server (port 5000)
echo "Creating firewall rule for port 5000..."
gcloud compute firewall-rules create allow-collision-detection-5000 \
    --allow tcp:5000 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow collision detection server on port 5000" \
    --target-tags http-server

# Create firewall rule for HTTP (port 80) if not exists
echo "Creating firewall rule for port 80..."
gcloud compute firewall-rules create allow-http-80 \
    --allow tcp:80 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow HTTP traffic on port 80" \
    --target-tags http-server

# Add network tags to your VM instance
echo "Adding network tags to VM instance..."
gcloud compute instances add-tags collision-detection-server \
    --tags http-server,https-server \
    --zone us-central1-a

echo "Firewall setup complete!"
echo ""
echo "Getting your VM's external IP address..."
EXTERNAL_IP=$(gcloud compute instances describe collision-detection-server \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "Your VM External IP: $EXTERNAL_IP"
echo ""
echo "Test your deployment:"
echo "  Web Interface: http://$EXTERNAL_IP:5000"
echo "  API Health:    http://$EXTERNAL_IP:5000/api/health"
echo ""
echo "If you still can't connect, wait 2-3 minutes for firewall rules to propagate."