# Collision Detection System

A comprehensive collision detection system that combines web-based simulation, computer vision, and IoT hardware control. The system processes uploaded videos and real-time camera feeds to detect collisions, provides visual feedback through a web interface, and can control ESP8266 hardware devices.

## 🏗️ Architecture

The system uses a distributed architecture with three main components:

- **Web Application** (`web/`): Browser-based simulation and control interface built with vanilla JavaScript
- **Raspberry Pi Server** (`raspberry-pi/`): Computer vision processing and hardware coordination using Python/Flask
- **ESP8266 Devices** (`esp8266-devices/`): IoT hardware controllers for physical responses programmed in C++

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │◄──►│  Raspberry Pi   │◄──►│ ESP8266 Devices │
│                 │    │     Server      │    │                 │
│ • Simulation    │    │ • Computer      │    │ • LED Control   │
│ • Video Upload  │    │   Vision        │    │ • Servo Control │
│ • Live Feeds    │    │ • Collision     │    │ • Relay Control │
│ • Hardware UI   │    │   Detection     │    │ • Status Report │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Node.js 16+** for web application
- **Python 3.8+** for Raspberry Pi server
- **PlatformIO** for ESP8266 development (optional)

### Setup Development Environment

**Windows:**
```batch
scripts\setup-dev-environment.bat
```

**Linux/macOS:**
```bash
./scripts/setup-dev-environment.sh
```

### Start Individual Components

1. **Web Application:**
   ```bash
   cd web
   npm start
   # Opens http://localhost:8080
   ```

2. **Raspberry Pi Server:**
   ```bash
   cd raspberry-pi
   source venv/bin/activate  # Windows: venv\Scripts\activate.bat
   python -m collision_server.main
   # Starts server on http://localhost:5000
   ```

3. **ESP8266 Device (optional):**
   ```bash
   cd esp8266-devices
   pio run --target upload
   ```

## 🧪 Testing

### Run All Tests
```bash
# Windows
scripts\test-all.bat

# Linux/macOS
./scripts/test-all.sh
```

### Component-Specific Tests

**Web Application:**
```bash
cd web
npm test                    # Run all tests
npm run test:property      # Run property-based tests only
```

**Raspberry Pi Server:**
```bash
cd raspberry-pi
source venv/bin/activate
python -m pytest          # Run all tests
python -m pytest -m property  # Run property tests only
```

**ESP8266 Firmware:**
```bash
cd esp8266-devices
pio test
```

## 📁 Project Structure

```
collision-detection-system/
├── web/                          # Web application
│   ├── src/
│   │   ├── core/                # Game objects and collision system
│   │   ├── video/               # Video upload and processing UI
│   │   ├── hardware/            # Hardware control interface
│   │   └── ui/                  # User interface components
│   ├── package.json
│   └── index.html
├── raspberry-pi/                 # Python server
│   ├── src/collision_server/
│   │   ├── core/                # Core collision detection
│   │   ├── video/               # Video processing
│   │   ├── cv/                  # Computer vision module
│   │   ├── hardware/            # Hardware communication
│   │   └── api/                 # REST API endpoints
│   ├── requirements.txt
│   └── setup.py
├── esp8266-devices/              # IoT hardware controllers
│   ├── src/                     # Main firmware code
│   ├── include/                 # Header files
│   ├── lib/                     # Custom libraries
│   └── platformio.ini
├── scripts/                      # Build and setup scripts
└── .kiro/specs/                  # Project specifications
```

## 🔧 Development

### Web Application
- **Framework:** Vanilla JavaScript with HTML5 Canvas
- **Testing:** Jest with fast-check for property-based testing
- **Build:** npm scripts with http-server for development

### Raspberry Pi Server
- **Framework:** Flask with SocketIO for real-time communication
- **Computer Vision:** OpenCV with PyTorch/YOLO for object detection
- **Testing:** pytest with Hypothesis for property-based testing

### ESP8266 Devices
- **Framework:** Arduino with PlatformIO
- **Communication:** WiFi with JSON over HTTP/WebSocket
- **Testing:** Unity test framework

## 📋 Features

### Web Simulation
- Interactive collision detection simulation
- Real-time physics with boundary handling
- User controls for object creation and parameter adjustment
- Visual feedback for collision events

### Video Analysis
- Upload support for MP4, AVI, MOV, WebM formats
- Computer vision-based object detection and tracking
- Collision detection in recorded footage
- Detailed analysis reports with timestamps

### Live Camera Processing
- Real-time camera feed processing
- Immediate collision alerts and notifications
- Multi-camera support
- Live video streaming to web interface

### Hardware Control
- ESP8266 device management and control
- LED, servo, and relay control capabilities
- Real-time status monitoring
- Automatic device discovery and registration

## 🎯 Requirements Coverage

The system implements all requirements from the specification:

- ✅ **Object Management** (Req 1): Create and manage simulation objects
- ✅ **Physics Simulation** (Req 2): Continuous movement with boundary collision
- ✅ **Collision Detection** (Req 3): AABB intersection with event triggering
- ✅ **Visual Feedback** (Req 4): Immediate collision response and visualization
- ✅ **User Interaction** (Req 5): Mouse and keyboard controls
- ✅ **Performance** (Req 6): Optimized algorithms for smooth operation
- ✅ **Web Standards** (Req 7): Cross-browser compatibility
- ✅ **Video Processing** (Req 8): Upload and analysis capabilities
- ✅ **Real-time Feeds** (Req 9): Live camera processing
- ✅ **Hardware Control** (Req 10): ESP8266 device management
- ✅ **Pi Integration** (Req 11): Raspberry Pi as processing hub
- ✅ **Computer Vision** (Req 12): Object detection and tracking

## 🧪 Property-Based Testing

The system uses property-based testing to verify correctness across all components:

- **21 Correctness Properties** covering all major functionality
- **Minimum 100 iterations** per property test
- **Universal quantification** ensuring properties hold for all valid inputs
- **Requirements traceability** linking each property to specific requirements

Example properties:
- Physics simulation accuracy across all objects and time deltas
- Collision detection accuracy with no false positives/negatives
- Video format validation for all supported formats
- Hardware command dispatch reliability

## 📖 Documentation

- **Requirements:** `.kiro/specs/collision-detection-web/requirements.md`
- **Design:** `.kiro/specs/collision-detection-web/design.md`
- **Tasks:** `.kiro/specs/collision-detection-web/tasks.md`
- **API Documentation:** Generated from code comments
- **Hardware Specs:** ESP8266 pin configurations and protocols

## 🤝 Contributing

1. Follow the established project structure
2. Write tests for all new functionality
3. Include property-based tests for universal behaviors
4. Update documentation for any API changes
5. Ensure cross-platform compatibility

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the component-specific README files
2. Review the specification documents in `.kiro/specs/`
3. Run the test suite to identify specific failures
4. Use VS Code workspace for integrated development experience