# Collision Detection System - Configuration Reference

## Overview

This document provides a comprehensive reference for all configuration options available in the Collision Detection System. Configuration is managed through environment variables, configuration files, and runtime settings.

## Configuration Hierarchy

Configuration settings are applied in the following order (later settings override earlier ones):

1. **Default Values**: Built-in system defaults
2. **Environment Variables**: System environment settings
3. **Configuration Files**: `.env` files and config files
4. **Runtime Settings**: Settings changed through the web interface
5. **Command Line Arguments**: Parameters passed at startup

## Raspberry Pi Server Configuration

### Environment Variables (.env file)

#### Server Configuration
```bash
# Basic server settings
HOST=0.0.0.0                    # Server bind address (0.0.0.0 for all interfaces)
PORT=5000                       # Server port number
DEBUG=False                     # Enable debug mode (True/False)
SECRET_KEY=your-secret-key      # Flask secret key for sessions
TESTING=False                   # Enable testing mode (True/False)

# SSL/HTTPS Configuration (optional)
SSL_CERT_PATH=/path/to/cert.pem # SSL certificate file path
SSL_KEY_PATH=/path/to/key.pem   # SSL private key file path
SSL_ENABLED=False               # Enable SSL/HTTPS (True/False)
```

#### File Storage Configuration
```bash
# Upload and storage paths
UPLOAD_FOLDER=/var/lib/collision-detection/uploads    # Video upload directory
LOG_DIRECTORY=/var/log/collision-detection            # Log file directory
MODEL_PATH=/var/lib/collision-detection/models       # AI model storage path
TEMP_DIRECTORY=/tmp/collision-temp                    # Temporary file directory

# File size and retention limits
MAX_CONTENT_LENGTH=524288000    # Maximum upload size (500MB in bytes)
MAX_VIDEO_DURATION=3600         # Maximum video length in seconds (1 hour)
FILE_RETENTION_DAYS=30          # Days to keep uploaded files
LOG_RETENTION_DAYS=90           # Days to keep log files
```

#### Database Configuration (Optional)
```bash
# Database connection (if using external database)
DATABASE_URL=sqlite:///collision.db                   # Database connection string
DATABASE_POOL_SIZE=10                                 # Connection pool size
DATABASE_TIMEOUT=30                                   # Connection timeout in seconds
DATABASE_ECHO=False                                   # Enable SQL query logging
```

#### Computer Vision Configuration
```bash
# AI/ML model settings
MODEL_PATH=/var/lib/collision-detection/models       # Model file directory
DEFAULT_MODEL=yolov8n.pt                             # Default detection model
CONFIDENCE_THRESHOLD=0.5                              # Detection confidence threshold (0.0-1.0)
COLLISION_THRESHOLD=0.7                               # Collision detection threshold (0.0-1.0)
NMS_THRESHOLD=0.4                                     # Non-maximum suppression threshold
MAX_DETECTIONS=100                                    # Maximum objects per frame

# Processing settings
ENABLE_GPU=True                                       # Use GPU acceleration if available
BATCH_SIZE=1                                          # Processing batch size
INPUT_SIZE=640                                        # Model input image size
ENABLE_TRACKING=True                                  # Enable object tracking
TRACKING_MAX_AGE=30                                   # Maximum tracking age in frames
```

#### Hardware Controller Configuration
```bash
# ESP8266 device communication
DISCOVERY_PORT=8888             # UDP port for device discovery
COMMAND_PORT=8889               # TCP port for sending commands
STATUS_PORT=8890                # TCP port for status updates
NETWORK_TIMEOUT=5.0             # Network operation timeout in seconds
DISCOVERY_INTERVAL=30.0         # Device discovery interval in seconds
MAX_RETRY_ATTEMPTS=3            # Maximum command retry attempts
DEVICE_TIMEOUT=60.0             # Device offline timeout in seconds

# Hardware response settings
ENABLE_AUTO_RESPONSE=True       # Enable automatic hardware responses
RESPONSE_DELAY=0.5              # Delay before hardware response in seconds
ALERT_DURATION=5.0              # Default alert duration in seconds
MAX_CONCURRENT_COMMANDS=10      # Maximum simultaneous commands
```

#### Performance and Resource Management
```bash
# Resource limits
MAX_WORKERS=4                   # Maximum worker processes
WORKER_TIMEOUT=300              # Worker timeout in seconds
MAX_MEMORY_MB=2048              # Maximum memory usage in MB
MAX_CPU_PERCENT=80              # Maximum CPU usage percentage
ENABLE_RESOURCE_MONITORING=True # Enable resource monitoring

# Processing optimization
RESOURCE_CONFIG=production      # Resource configuration profile (development/production)
ENABLE_CACHING=True             # Enable result caching
CACHE_SIZE_MB=512               # Cache size in MB
CACHE_TTL=3600                  # Cache time-to-live in seconds
ENABLE_COMPRESSION=True         # Enable response compression
```

#### Monitoring and Logging
```bash
# System monitoring
ENABLE_MONITORING=True          # Enable system monitoring
MONITORING_INTERVAL=10          # Monitoring update interval in seconds
PERFORMANCE_LOGGING=True        # Enable performance logging
ALERT_THRESHOLD_CPU=80          # CPU usage alert threshold (%)
ALERT_THRESHOLD_MEMORY=85       # Memory usage alert threshold (%)
ALERT_THRESHOLD_DISK=90         # Disk usage alert threshold (%)
ALERT_THRESHOLD_TEMP=70         # Temperature alert threshold (°C)

# Logging configuration
LOG_LEVEL=INFO                  # Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
LOG_FORMAT=detailed             # Log format (simple/detailed/json)
ENABLE_FILE_LOGGING=True        # Enable file logging
ENABLE_CONSOLE_LOGGING=True     # Enable console logging
MAX_LOG_SIZE_MB=100             # Maximum log file size in MB
LOG_BACKUP_COUNT=5              # Number of log backup files to keep
```

### Advanced Configuration Files

#### Computer Vision Configuration (cv_config.yaml)
```yaml
# Object detection settings
detection:
  model_name: "yolov8n.pt"
  confidence_threshold: 0.5
  nms_threshold: 0.4
  max_detections: 100
  input_size: 640
  
  # Class filtering
  enabled_classes:
    - person
    - bicycle
    - car
    - motorcycle
    - bus
    - truck
  
  # Detection zones (optional)
  zones:
    - name: "main_area"
      coordinates: [[0, 0], [640, 0], [640, 480], [0, 480]]
      enabled: true
    - name: "restricted_area"
      coordinates: [[100, 100], [540, 100], [540, 380], [100, 380]]
      enabled: false

# Object tracking settings
tracking:
  enabled: true
  max_age: 30
  min_hits: 3
  iou_threshold: 0.3
  
# Collision detection settings
collision:
  threshold: 0.7
  min_overlap: 0.3
  velocity_threshold: 5.0
  time_threshold: 1.0
  
  # Collision rules
  rules:
    - name: "vehicle_collision"
      classes: ["car", "truck", "bus"]
      min_velocity: 10.0
      severity: "high"
    - name: "pedestrian_collision"
      classes: ["person", "bicycle"]
      min_velocity: 2.0
      severity: "critical"
```

#### Hardware Configuration (hardware_config.yaml)
```yaml
# Device discovery settings
discovery:
  enabled: true
  interval: 30
  timeout: 5
  max_devices: 50
  
# Device types and capabilities
device_types:
  esp8266_basic:
    capabilities: ["led_control", "status_reporting"]
    max_response_time: 2.0
  esp8266_advanced:
    capabilities: ["led_control", "servo_control", "relay_control", "sensor_reading"]
    max_response_time: 1.0
    
# Alert configurations
alerts:
  collision_detected:
    led_pattern: "flash_red"
    duration: 5.0
    priority: "high"
  system_warning:
    led_pattern: "solid_yellow"
    duration: 10.0
    priority: "medium"
  system_error:
    led_pattern: "flash_red_fast"
    duration: 15.0
    priority: "critical"
    
# LED patterns
led_patterns:
  solid_red:
    type: "solid"
    color: [255, 0, 0]
  flash_red:
    type: "flash"
    color: [255, 0, 0]
    interval: 0.5
  flash_red_fast:
    type: "flash"
    color: [255, 0, 0]
    interval: 0.2
  solid_yellow:
    type: "solid"
    color: [255, 255, 0]
```

## ESP8266 Device Configuration

### Main Configuration (include/config.h)
```cpp
// Network Configuration
#define WIFI_SSID "YourNetworkName"
#define WIFI_PASSWORD "YourNetworkPassword"
#define RASPBERRY_PI_IP "192.168.1.100"
#define WIFI_CONNECT_TIMEOUT_MS 30000
#define MAX_WIFI_RECONNECT_ATTEMPTS 5
#define WIFI_RECONNECT_INTERVAL_MS 10000

// Device Identification
#define DEVICE_ID_PREFIX "ESP8266_"
#define FIRMWARE_VERSION "1.0.0"
#define DEVICE_TYPE "collision_detector"

// Server Communication
#define SERVER_PORT 80
#define API_ENDPOINT "/api/hardware"
#define HEARTBEAT_INTERVAL_MS 30000
#define STATUS_UPDATE_INTERVAL_MS 10000
#define COMMAND_TIMEOUT_MS 5000
#define MAX_RETRY_ATTEMPTS 3

// Hardware Pin Assignments
#define LED_RED_PIN D1
#define LED_GREEN_PIN D2
#define LED_BLUE_PIN D3
#define SERVO_PIN D4
#define RELAY_PIN D5
#define STATUS_LED_PIN D0
#define BUZZER_PIN D6
#define SENSOR_PIN A0

// Performance Settings
#define LOOP_DELAY_MS 100
#define JSON_BUFFER_SIZE 1024
#define COMMAND_QUEUE_SIZE 10
#define STATUS_BUFFER_SIZE 512

// Feature Enables
#define ENABLE_LED_CONTROL true
#define ENABLE_SERVO_CONTROL true
#define ENABLE_RELAY_CONTROL true
#define ENABLE_SENSOR_READING true
#define ENABLE_OTA_UPDATES true
#define ENABLE_SERIAL_DEBUG true

// Safety and Limits
#define MAX_SERVO_ANGLE 180
#define MIN_SERVO_ANGLE 0
#define SERVO_SPEED_LIMIT 100
#define MAX_LED_BRIGHTNESS 255
#define RELAY_MAX_ON_TIME_MS 60000
#define TEMPERATURE_LIMIT_C 80.0
#define VOLTAGE_MIN_V 3.0
#define VOLTAGE_MAX_V 3.6

// Debugging and Monitoring
#define DEBUG_SERIAL_BAUD 115200
#define ENABLE_WATCHDOG true
#define WATCHDOG_TIMEOUT_MS 8000
#define ENABLE_PERFORMANCE_MONITORING true
#define MEMORY_CHECK_INTERVAL_MS 60000
```

### Advanced Device Configuration (device_config.json)
```json
{
  "device": {
    "id": "ESP8266_001",
    "type": "collision_detector",
    "location": "Main Entrance",
    "description": "Primary collision detection device"
  },
  
  "network": {
    "wifi": {
      "ssid": "YourNetwork",
      "password": "YourPassword",
      "static_ip": {
        "enabled": false,
        "ip": "192.168.1.150",
        "gateway": "192.168.1.1",
        "subnet": "255.255.255.0",
        "dns": "8.8.8.8"
      }
    },
    "server": {
      "ip": "192.168.1.100",
      "port": 5000,
      "ssl": false
    }
  },
  
  "hardware": {
    "leds": {
      "red": {"pin": 5, "enabled": true},
      "green": {"pin": 4, "enabled": true},
      "blue": {"pin": 0, "enabled": true}
    },
    "servo": {
      "pin": 2,
      "enabled": true,
      "min_angle": 0,
      "max_angle": 180,
      "default_angle": 90
    },
    "relay": {
      "pin": 14,
      "enabled": true,
      "default_state": false,
      "max_on_time": 60000
    },
    "sensors": {
      "temperature": {"pin": "A0", "enabled": true},
      "voltage": {"enabled": true}
    }
  },
  
  "behavior": {
    "heartbeat_interval": 30000,
    "status_interval": 10000,
    "command_timeout": 5000,
    "auto_restart": true,
    "watchdog_enabled": true
  },
  
  "alerts": {
    "collision": {
      "led_color": [255, 0, 0],
      "flash_rate": 2,
      "duration": 5000,
      "servo_action": "sweep",
      "relay_action": "pulse"
    },
    "warning": {
      "led_color": [255, 255, 0],
      "flash_rate": 1,
      "duration": 3000
    },
    "error": {
      "led_color": [255, 0, 0],
      "flash_rate": 5,
      "duration": 10000
    }
  }
}
```

## Web Interface Configuration

### Client-Side Configuration (config.js)
```javascript
// API Configuration
const CONFIG = {
  // Server settings
  server: {
    baseUrl: 'http://localhost:5000',
    apiPath: '/api',
    wsPath: '/socket.io',
    timeout: 30000
  },
  
  // Video settings
  video: {
    maxFileSize: 500 * 1024 * 1024, // 500MB
    supportedFormats: ['mp4', 'avi', 'mov', 'webm'],
    defaultQuality: 'medium',
    processingTimeout: 300000 // 5 minutes
  },
  
  // Camera settings
  camera: {
    defaultResolution: '640x480',
    defaultFps: 30,
    maxCameras: 4,
    reconnectInterval: 5000,
    streamTimeout: 10000
  },
  
  // Hardware settings
  hardware: {
    discoveryInterval: 30000,
    commandTimeout: 5000,
    maxRetries: 3,
    statusUpdateInterval: 10000
  },
  
  // UI settings
  ui: {
    theme: 'light',
    autoRefresh: true,
    refreshInterval: 10000,
    notifications: true,
    soundAlerts: false,
    animationSpeed: 300
  },
  
  // Performance settings
  performance: {
    enableCaching: true,
    cacheTimeout: 300000,
    maxConcurrentRequests: 5,
    enableCompression: true
  },
  
  // Monitoring settings
  monitoring: {
    enabled: true,
    updateInterval: 10000,
    historyDuration: 3600000, // 1 hour
    alertThresholds: {
      cpu: 80,
      memory: 85,
      disk: 90
    }
  }
};
```

## Runtime Configuration

### API Configuration Endpoints

#### System Settings
```http
GET /api/config/system
POST /api/config/system
{
  "debug_mode": false,
  "log_level": "INFO",
  "max_workers": 4,
  "enable_monitoring": true
}
```

#### Computer Vision Settings
```http
GET /api/config/cv
POST /api/config/cv
{
  "confidence_threshold": 0.5,
  "collision_threshold": 0.7,
  "enable_tracking": true,
  "model_name": "yolov8n.pt"
}
```

#### Hardware Settings
```http
GET /api/config/hardware
POST /api/config/hardware
{
  "discovery_interval": 30,
  "command_timeout": 5,
  "enable_auto_response": true,
  "alert_duration": 5
}
```

#### Camera Settings
```http
GET /api/config/camera
POST /api/config/camera
{
  "default_resolution": "640x480",
  "default_fps": 30,
  "detection_enabled": true,
  "recording_enabled": false
}
```

## Configuration Validation

### Environment Variable Validation
```python
# Example validation rules
VALIDATION_RULES = {
    'HOST': {'type': str, 'default': '0.0.0.0'},
    'PORT': {'type': int, 'min': 1, 'max': 65535, 'default': 5000},
    'DEBUG': {'type': bool, 'default': False},
    'CONFIDENCE_THRESHOLD': {'type': float, 'min': 0.0, 'max': 1.0, 'default': 0.5},
    'MAX_CONTENT_LENGTH': {'type': int, 'min': 1024, 'default': 524288000},
    'DISCOVERY_INTERVAL': {'type': float, 'min': 1.0, 'default': 30.0}
}
```

### Configuration File Validation
```yaml
# JSON Schema for configuration validation
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "server": {
      "type": "object",
      "properties": {
        "host": {"type": "string"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "debug": {"type": "boolean"}
      },
      "required": ["host", "port"]
    },
    "detection": {
      "type": "object",
      "properties": {
        "confidence_threshold": {"type": "number", "minimum": 0, "maximum": 1},
        "collision_threshold": {"type": "number", "minimum": 0, "maximum": 1}
      }
    }
  }
}
```

## Configuration Best Practices

### Security Considerations
1. **Never commit sensitive data** (passwords, keys) to version control
2. **Use environment variables** for sensitive configuration
3. **Validate all input** from configuration files
4. **Use secure defaults** for all settings
5. **Regularly rotate secrets** and credentials

### Performance Optimization
1. **Tune resource limits** based on hardware capabilities
2. **Adjust processing quality** based on requirements
3. **Configure appropriate timeouts** for network operations
4. **Enable caching** for frequently accessed data
5. **Monitor resource usage** and adjust accordingly

### Maintenance Guidelines
1. **Document all configuration changes**
2. **Test configuration changes** in development first
3. **Backup configuration files** before changes
4. **Use version control** for configuration files
5. **Regular configuration audits** for security and performance

This configuration reference provides comprehensive documentation for all configurable aspects of the collision detection system.