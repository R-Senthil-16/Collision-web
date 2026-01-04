# Google Cloud Setup - Step by Step

## Part 1: Commands on YOUR LOCAL COMPUTER

### Step 1: Create VM (Run on your computer)
```bash
# Option A: Use Google Cloud Console (Web Browser)
# Go to https://console.cloud.google.com
# Navigate to Compute Engine > VM instances > Create Instance

# Option B: Use gcloud CLI (if installed on your computer)
gcloud compute instances create collision-detection-server \
    --zone=us-central1-a \
    --machine-type=e2-standard-2 \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --tags=http-server,https-server
```

### Step 2: Configure Firewall (Run on your computer)
```bash
# Only if using gcloud CLI
gcloud compute firewall-rules create allow-collision-detection \
    --allow tcp:5000 \
    --source-ranges 0.0.0.0/0

gcloud compute firewall-rules create allow-http \
    --allow tcp:80 \
    --source-ranges 0.0.0.0/0
```

### Step 3: SSH into VM (Run on your computer)
```bash
# Option A: Use gcloud CLI
gcloud compute ssh collision-detection-server --zone=us-central1-a

# Option B: Use SSH button in Google Cloud Console (easier)
# Click "SSH" button next to your VM in the console
```

---

## Part 2: Commands INSIDE THE GOOGLE CLOUD VM

### After SSH connection, you'll see a terminal like:
```
username@collision-detection-server:~$
```

### Step 4: Install Dependencies (Run INSIDE VM)
```bash
# You are now inside the Google Cloud VM
# Run these commands in the VM terminal:

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git nginx
sudo apt install -y python3-opencv libopencv-dev
sudo apt install -y build-essential cmake pkg-config
sudo apt install -y libjpeg-dev libtiff5-dev libpng-dev
sudo apt install -y libavcodec-dev libavformat-dev libswscale-dev
sudo apt install -y libatlas-base-dev gfortran
```

### Step 5: Clone Repository (Run INSIDE VM)
```bash
# Still inside the VM
# You should be in /home/yourusername directory

pwd  # This should show: /home/yourusername

# Clone your repository
git clone https://github.com/yourusername/Collision-web.git
cd Collision-web
```

### Step 6: Setup Python Environment (Run INSIDE VM)
```bash
# Navigate to raspberry-pi directory
cd raspberry-pi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 7: Configure Environment (Run INSIDE VM)
```bash
# Create environment file
cp .env.example .env
nano .env  # or use vim .env
```

### Step 8: Create Directories (Run INSIDE VM)
```bash
# Create upload and log directories
mkdir -p ~/collision-uploads ~/collision-logs
```

### Step 9: Test the Server (Run INSIDE VM)
```bash
# Make sure you're in the right directory
cd ~/Collision-web/raspberry-pi
source venv/bin/activate

# Set environment variables
export UPLOAD_FOLDER=/home/$(whoami)/collision-uploads
export LOG_DIRECTORY=/home/$(whoami)/collision-logs

# Run the server
python -m collision_server.main
```

---

## Visual Guide:

```
YOUR COMPUTER                    GOOGLE CLOUD VM
┌─────────────────┐             ┌──────────────────────┐
│                 │   SSH       │                      │
│ 1. Create VM    │ ────────────► │ 4. Install deps     │
│ 2. Setup        │             │ 5. Clone repo        │
│    firewall     │             │ 6. Setup Python      │
│ 3. SSH connect  │             │ 7. Configure .env    │
│                 │             │ 8. Run server        │
└─────────────────┘             └──────────────────────┘
```

## Quick Answer for Step 5:

**Step 5 commands should be run INSIDE the Google Cloud VM, NOT as root.**

When you SSH into the VM, you'll be logged in as your regular user (not root). Run the commands as this user:

```bash
# You'll see a prompt like this:
yourusername@collision-detection-server:~$ 

# Run the Step 5 commands here:
cp .env.example .env
nano .env
```

## If You Need Root Access:

Only use `sudo` for system-level commands like installing packages:

```bash
# Use sudo for system packages
sudo apt install python3-pip

# DON'T use sudo for your application
# WRONG: sudo python -m collision_server.main
# RIGHT: python -m collision_server.main
```

## Easy Alternative - One Command Setup:

Instead of all the manual steps, you can run this single command INSIDE the VM:

```bash
# After SSH into VM, run this one command:
curl -sSL https://raw.githubusercontent.com/yourusername/Collision-web/main/scripts/gcp-setup.sh | bash
```

This will do all the setup automatically!