#!/bin/bash

# Collision Detection System - Development Environment Setup Script
# This script sets up the complete development environment for all components

set -e  # Exit on any error

echo "🚀 Setting up Collision Detection System Development Environment"
echo "=============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on supported OS
check_os() {
    print_status "Checking operating system..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_success "Linux detected"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        print_success "macOS detected"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        print_success "Windows detected"
    else
        print_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
}

# Check for required system dependencies
check_dependencies() {
    print_status "Checking system dependencies..."
    
    # Check for Node.js and npm
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 16+ from https://nodejs.org/"
        exit 1
    fi
    
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 16 ]; then
        print_error "Node.js version 16+ required. Current version: $(node --version)"
        exit 1
    fi
    print_success "Node.js $(node --version) found"
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8+ from https://python.org/"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
    print_success "Python $(python3 --version) found"
    
    # Check for pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install pip3"
        exit 1
    fi
    print_success "pip3 found"
    
    # Check for PlatformIO (optional, will install if not found)
    if ! command -v pio &> /dev/null; then
        print_warning "PlatformIO CLI not found. Will install during ESP8266 setup."
    else
        print_success "PlatformIO CLI found"
    fi
}

# Setup Web Application
setup_web() {
    print_status "Setting up Web Application..."
    
    cd web
    
    # Install npm dependencies
    print_status "Installing npm dependencies..."
    npm install
    
    # Create necessary directories
    mkdir -p src/core src/video src/hardware src/ui src/__tests__
    
    print_success "Web application setup complete"
    cd ..
}

# Setup Raspberry Pi Server
setup_raspberry_pi() {
    print_status "Setting up Raspberry Pi Server..."
    
    cd raspberry-pi
    
    # Create virtual environment
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
    
    # Activate virtual environment and install dependencies
    print_status "Installing Python dependencies..."
    if [[ "$OS" == "windows" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Create necessary directories
    mkdir -p src/collision_server/{core,video,hardware,cv,api} tests logs uploads processed models
    
    # Create __init__.py files
    touch src/__init__.py
    touch src/collision_server/__init__.py
    touch src/collision_server/core/__init__.py
    touch src/collision_server/video/__init__.py
    touch src/collision_server/hardware/__init__.py
    touch src/collision_server/cv/__init__.py
    touch src/collision_server/api/__init__.py
    
    # Copy environment file
    if [ ! -f .env ]; then
        cp .env.example .env
        print_warning "Created .env file from template. Please update with your configuration."
    fi
    
    deactivate
    print_success "Raspberry Pi server setup complete"
    cd ..
}

# Setup ESP8266 Development
setup_esp8266() {
    print_status "Setting up ESP8266 Development Environment..."
    
    cd esp8266-devices
    
    # Install PlatformIO if not already installed
    if ! command -v pio &> /dev/null; then
        print_status "Installing PlatformIO..."
        if [[ "$OS" == "windows" ]]; then
            print_warning "Please install PlatformIO manually from https://platformio.org/install/cli"
        else
            curl -fsSL https://raw.githubusercontent.com/platformio/platformio-core-installer/master/get-platformio.py -o get-platformio.py
            python3 get-platformio.py
            rm get-platformio.py
            
            # Add to PATH
            export PATH=$PATH:~/.platformio/penv/bin
            echo 'export PATH=$PATH:~/.platformio/penv/bin' >> ~/.bashrc
        fi
    fi
    
    # Create necessary directories
    mkdir -p src test include/device_types lib/DeviceController/src lib/DeviceController/include
    
    # Initialize PlatformIO project (if pio is available)
    if command -v pio &> /dev/null; then
        print_status "Installing PlatformIO dependencies..."
        pio lib install
        print_success "ESP8266 development environment setup complete"
    else
        print_warning "PlatformIO not available. ESP8266 setup incomplete."
    fi
    
    cd ..
}

# Create project-wide configuration
create_project_config() {
    print_status "Creating project configuration..."
    
    # Create main project README
    cat > README.md << 'EOF'
# Collision Detection System

A comprehensive collision detection system that combines web-based simulation, computer vision, and IoT hardware control.

## Architecture

- **Web Application** (`web/`): Browser-based simulation and control interface
- **Raspberry Pi Server** (`raspberry-pi/`): Computer vision processing and hardware coordination
- **ESP8266 Devices** (`esp8266-devices/`): IoT hardware controllers for physical responses

## Quick Start

1. **Setup Development Environment**:
   ```bash
   ./scripts/setup-dev-environment.sh
   ```

2. **Start Web Application**:
   ```bash
   cd web
   npm start
   ```

3. **Start Raspberry Pi Server**:
   ```bash
   cd raspberry-pi
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   python -m collision_server.main
   ```

4. **Flash ESP8266 Device**:
   ```bash
   cd esp8266-devices
   pio run --target upload
   ```

## Development

- **Web**: JavaScript with Canvas API, Jest for testing
- **Server**: Python with Flask, OpenCV, PyTorch
- **Hardware**: C++ with Arduino framework, PlatformIO

## Testing

- **Web**: `cd web && npm test`
- **Server**: `cd raspberry-pi && python -m pytest`
- **Hardware**: `cd esp8266-devices && pio test`

See individual component READMEs for detailed information.
EOF

    # Create VS Code workspace configuration
    cat > collision-detection.code-workspace << 'EOF'
{
    "folders": [
        {
            "name": "Web Application",
            "path": "./web"
        },
        {
            "name": "Raspberry Pi Server",
            "path": "./raspberry-pi"
        },
        {
            "name": "ESP8266 Devices",
            "path": "./esp8266-devices"
        },
        {
            "name": "Scripts",
            "path": "./scripts"
        }
    ],
    "settings": {
        "python.defaultInterpreterPath": "./raspberry-pi/venv/bin/python",
        "python.testing.pytestEnabled": true,
        "python.testing.pytestArgs": ["raspberry-pi/tests"],
        "javascript.preferences.includePackageJsonAutoImports": "auto",
        "platformio-ide.useBuiltinPIOCore": true,
        "platformio-ide.activateOnlyOnPlatformIOProject": false
    },
    "extensions": {
        "recommendations": [
            "ms-python.python",
            "ms-python.black-formatter",
            "ms-python.flake8",
            "ms-python.mypy-type-checker",
            "platformio.platformio-ide",
            "ms-vscode.cpptools",
            "bradlc.vscode-tailwindcss",
            "esbenp.prettier-vscode"
        ]
    }
}
EOF

    print_success "Project configuration created"
}

# Create build and run scripts
create_scripts() {
    print_status "Creating build and run scripts..."
    
    # Build all script
    cat > scripts/build-all.sh << 'EOF'
#!/bin/bash
set -e

echo "🔨 Building all components..."

# Build web application
echo "Building web application..."
cd web
npm run build
cd ..

# Build Raspberry Pi server
echo "Building Raspberry Pi server..."
cd raspberry-pi
source venv/bin/activate || source venv/Scripts/activate
python setup.py build
deactivate
cd ..

# Build ESP8266 firmware
echo "Building ESP8266 firmware..."
cd esp8266-devices
if command -v pio &> /dev/null; then
    pio run
else
    echo "PlatformIO not available, skipping ESP8266 build"
fi
cd ..

echo "✅ All components built successfully"
EOF

    # Test all script
    cat > scripts/test-all.sh << 'EOF'
#!/bin/bash
set -e

echo "🧪 Running all tests..."

# Test web application
echo "Testing web application..."
cd web
npm test
cd ..

# Test Raspberry Pi server
echo "Testing Raspberry Pi server..."
cd raspberry-pi
source venv/bin/activate || source venv/Scripts/activate
python -m pytest
deactivate
cd ..

# Test ESP8266 firmware
echo "Testing ESP8266 firmware..."
cd esp8266-devices
if command -v pio &> /dev/null; then
    pio test
else
    echo "PlatformIO not available, skipping ESP8266 tests"
fi
cd ..

echo "✅ All tests completed"
EOF

    # Make scripts executable
    chmod +x scripts/build-all.sh
    chmod +x scripts/test-all.sh
    
    print_success "Build and test scripts created"
}

# Main setup function
main() {
    print_status "Starting development environment setup..."
    
    check_os
    check_dependencies
    setup_web
    setup_raspberry_pi
    setup_esp8266
    create_project_config
    create_scripts
    
    print_success "🎉 Development environment setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Review and update raspberry-pi/.env with your configuration"
    echo "2. Start development with: cd web && npm start"
    echo "3. Open collision-detection.code-workspace in VS Code for full IDE support"
    echo ""
    echo "For more information, see README.md"
}

# Run main function
main "$@"