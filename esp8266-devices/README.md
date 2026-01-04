# ESP8266 Collision Detection Device Firmware

This firmware implements a collision detection response system for ESP8266 microcontrollers. When collision events are detected by the Raspberry Pi server, this device can trigger various hardware responses including LED alerts, servo movements, relay switching, and buzzer notifications.

## Features

- **WiFi Connectivity**: Automatic connection and reconnection to WiFi networks
- **Hardware Control**: Support for LEDs, servos, relays, and buzzers
- **Command Processing**: JSON-based command reception and execution
- **Status Reporting**: Real-time device status and health monitoring
- **Health Monitoring**: Comprehensive system health tracking and alerting
- **OTA Updates**: Over-the-air firmware update capability
- **Web Interface**: Built-in web server for device management

## Hardware Requirements

- ESP8266 development board (NodeMCU v2 recommended)
- RGB LED (connected to pins D1, D2, D3)
- Servo motor (connected to pin D4)
- Relay module (connected to pin D5)
- Buzzer (connected to pin D6)
- Status LED (connected to pin D7)
- Push button (connected to pin D8)

## Pin Configuration

| Component | Pin | Description |
|-----------|-----|-------------|
| Red LED | D1 | Red channel of RGB LED |
| Green LED | D2 | Green channel of RGB LED |
| Blue LED | D3 | Blue channel of RGB LED |
| Servo | D4 | PWM control for servo motor |
| Relay | D5 | Digital control for relay |
| Buzzer | D6 | PWM control for buzzer |
| Status LED | D7 | Device status indicator |
| Button | D8 | User input button |

## Software Architecture

### Core Components

1. **DeviceController**: Manages hardware control and command execution
2. **HealthMonitor**: Tracks system health and generates alerts
3. **WiFi Manager**: Handles network connectivity and reconnection
4. **Web Server**: Provides HTTP API for device control
5. **Command Processor**: Parses and executes JSON commands

### Communication Protocol

The device communicates with the Raspberry Pi server using JSON messages over HTTP. Supported command types:

- `led_control`: Control RGB LED colors and patterns
- `servo_control`: Move servo to specific angles or sweep patterns
- `relay_control`: Switch relay on/off
- `buzzer_control`: Generate beep patterns
- `status_request`: Request device status information

### Example Commands

```json
{
  "command": "led_control",
  "device_id": "COL_ABCDEF",
  "action": "on",
  "color": {"r": 255, "g": 0, "b": 0},
  "intensity": 255
}
```

```json
{
  "command": "servo_control",
  "device_id": "COL_ABCDEF",
  "action": "move",
  "angle": 90
}
```

## Building and Deployment

### Prerequisites

- PlatformIO IDE or CLI
- ESP8266 development environment
- USB cable for programming

### Build Commands

```bash
# Build for ESP8266
pio run -e esp8266_generic

# Upload firmware
pio run -e esp8266_generic -t upload

# Monitor serial output
pio device monitor

# Run tests
pio test -e native
```

### Configuration

1. Update WiFi credentials in the web interface or modify `main.cpp`
2. Set Raspberry Pi IP address for status reporting
3. Adjust hardware pin assignments in `config.h` if needed

## API Endpoints

The device exposes the following HTTP endpoints:

- `GET /` - Device information page
- `GET /status` - JSON status response
- `POST /command` - Execute hardware command
- `GET /health` - Health monitoring report
- `GET /diagnostics` - System diagnostics
- `GET /alerts` - Active alerts list
- `POST /config` - Update device configuration

## Health Monitoring

The firmware includes comprehensive health monitoring:

- **System Metrics**: Memory usage, CPU load, uptime
- **Network Metrics**: WiFi signal strength, connection status
- **Hardware Metrics**: Temperature, voltage, component status
- **Performance Metrics**: Loop timing, command processing speed
- **Alert System**: Automatic threshold monitoring and notifications

## Testing

The firmware includes comprehensive unit tests covering:

- Device controller functionality
- Health monitoring system
- Communication protocol validation
- Command parsing and execution
- Hardware control operations

Run tests with: `pio test -e native`

## Troubleshooting

### Common Issues

1. **WiFi Connection Failed**
   - Check SSID and password
   - Verify network is 2.4GHz (ESP8266 doesn't support 5GHz)
   - Check signal strength

2. **Hardware Not Responding**
   - Verify pin connections
   - Check power supply (3.3V for ESP8266)
   - Review serial monitor for error messages

3. **Commands Not Executing**
   - Verify JSON format
   - Check device ID matches
   - Ensure Raspberry Pi can reach device IP

### Debug Information

Enable debug output by setting `DEBUG=1` in build flags. Monitor serial output at 115200 baud for detailed logging.

## License

This firmware is part of the Collision Detection System project. See the main project README for license information.