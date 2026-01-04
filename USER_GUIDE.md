# Collision Detection System - User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Web Interface Overview](#web-interface-overview)
3. [Video Analysis](#video-analysis)
4. [Live Camera Monitoring](#live-camera-monitoring)
5. [Hardware Control](#hardware-control)
6. [System Monitoring](#system-monitoring)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

## Getting Started

### System Overview

The Collision Detection System is a comprehensive platform that combines:
- **Video Analysis**: Upload and analyze recorded videos for collision events
- **Live Monitoring**: Real-time collision detection from camera feeds
- **Hardware Control**: Automated responses via ESP8266 devices
- **System Monitoring**: Performance tracking and health monitoring

### Accessing the System

1. **Web Interface**: Open your browser and navigate to `http://raspberry-pi-ip/`
2. **Default Access**: The system is accessible on the local network
3. **No Login Required**: The system operates without user authentication by default

### System Status Indicators

- **Green**: System healthy and operational
- **Yellow**: Warning conditions detected
- **Red**: Error conditions or system offline
- **Gray**: Component offline or not configured

## Web Interface Overview

### Navigation Tabs

The web interface consists of four main tabs:

1. **Video Analysis**: Upload and process recorded videos
2. **Live Feed**: Monitor real-time camera feeds
3. **Hardware Control**: Manage ESP8266 devices
4. **System Monitor**: View system health and performance

### Common Controls

- **Refresh Button**: Update current data
- **Status Indicators**: Show component health
- **Progress Bars**: Display processing status
- **Alert Notifications**: Show system alerts

## Video Analysis

### Uploading Videos

1. **Navigate** to the Video Analysis tab
2. **Click** "Choose File" or drag and drop a video file
3. **Supported Formats**: MP4, AVI, MOV, WebM
4. **File Size Limit**: 500MB maximum
5. **Click** "Upload" to begin processing

### Processing Status

- **Uploading**: File transfer in progress
- **Processing**: Computer vision analysis running
- **Completed**: Analysis finished, results available
- **Failed**: Error occurred during processing

### Viewing Results

Once processing is complete:

1. **Collision Events**: List of detected collisions with timestamps
2. **Video Player**: Playback with collision markers
3. **Object Tracking**: Visualization of detected objects
4. **Export Options**: Download results as JSON or CSV

### Analysis Settings

Configure detection parameters:

- **Confidence Threshold**: Minimum detection confidence (0.1-1.0)
- **Collision Sensitivity**: How sensitive collision detection is
- **Object Types**: Which objects to detect (vehicles, people, etc.)
- **Processing Quality**: Balance between speed and accuracy

## Live Camera Monitoring

### Camera Setup

1. **Connect Camera**: USB camera or Raspberry Pi camera module
2. **Camera Selection**: Choose from available cameras
3. **Resolution Settings**: Configure video resolution and frame rate
4. **Detection Settings**: Set real-time detection parameters

### Starting Live Monitoring

1. **Select Camera**: Choose camera from dropdown
2. **Configure Settings**: Adjust resolution and detection parameters
3. **Click Connect**: Start live video feed
4. **Monitor Display**: View live feed with collision overlays

### Real-Time Alerts

When collisions are detected:

1. **Visual Alerts**: Red overlay on video feed
2. **Audio Notifications**: Browser alert sounds (if enabled)
3. **Hardware Triggers**: Automatic ESP8266 device activation
4. **Log Entries**: Collision events logged with timestamps

### Camera Controls

- **Start/Stop**: Begin or end camera monitoring
- **Switch Camera**: Change between multiple cameras
- **Snapshot**: Capture still images
- **Recording**: Save video segments (if configured)

## Hardware Control

### Device Management

#### Device Discovery

1. **Automatic Discovery**: System scans for ESP8266 devices
2. **Manual Refresh**: Click "Discover Devices" to rescan
3. **Device List**: Shows all connected devices with status
4. **Connection Status**: Online/Offline indicators

#### Device Information

For each device, view:
- **Device ID**: Unique identifier
- **IP Address**: Network location
- **Status**: Online, offline, or error
- **Capabilities**: Available hardware (LEDs, servos, relays)
- **Last Seen**: Time of last communication

### Manual Control

#### LED Control
```
Test All LEDs: Flash all LED indicators
Individual Control: Set specific colors and brightness
Pattern Control: Configure blinking patterns
```

#### Servo Control
```
Test All Servos: Move servos to test positions
Position Control: Set specific servo angles
Speed Control: Adjust movement speed
```

#### Relay Control
```
Test All Relays: Toggle all relay outputs
Individual Control: Control specific relays
Timer Control: Set automatic on/off timers
```

### Automated Responses

Configure automatic hardware responses to collision events:

1. **Alert Patterns**: Define LED flash patterns for different alert types
2. **Servo Actions**: Configure servo movements for collision responses
3. **Relay Triggers**: Set relay activations for external devices
4. **Response Delays**: Configure timing for hardware responses

### Device Logs

Monitor device activity:
- **Command History**: Log of sent commands
- **Response Times**: Device response performance
- **Error Messages**: Hardware communication errors
- **Status Updates**: Device health and status changes

## System Monitoring

### System Health Dashboard

#### Overall Status
- **System Health**: Overall system status indicator
- **Component Status**: Individual component health
- **Active Alerts**: Current system alerts
- **Performance Metrics**: CPU, memory, and disk usage

#### Performance Monitoring

**Real-Time Metrics**:
- CPU Usage: Current processor utilization
- Memory Usage: RAM consumption
- Disk Usage: Storage space utilization
- Network Activity: Data transfer rates
- Temperature: System temperature (if available)

**Historical Data**:
- Performance graphs over time
- Trend analysis
- Peak usage identification
- Performance optimization recommendations

### Alert Management

#### Alert Types
- **Info**: Informational messages
- **Warning**: Potential issues requiring attention
- **Error**: Problems affecting functionality
- **Critical**: Severe issues requiring immediate action

#### Alert Actions
- **View Details**: See full alert information
- **Acknowledge**: Mark alert as seen
- **Resolve**: Mark issue as fixed
- **Export**: Save alert history

### System Logs

#### Log Categories
- **System**: General system operations
- **Performance**: Performance metrics and statistics
- **Errors**: Error messages and exceptions
- **Alerts**: Alert generation and resolution

#### Log Viewing
- **Real-Time**: Live log streaming
- **Historical**: Browse past log entries
- **Filtering**: Filter by date, level, or component
- **Search**: Find specific log entries
- **Export**: Download log files

## Configuration

### System Settings

#### Video Processing
```
Detection Confidence: 0.5 (recommended)
Processing Quality: High/Medium/Low
Max Video Size: 500MB
Supported Formats: MP4, AVI, MOV, WebM
```

#### Camera Settings
```
Default Resolution: 640x480
Frame Rate: 30 FPS
Detection Threshold: 0.7
Buffer Size: 10 frames
```

#### Hardware Settings
```
Discovery Interval: 30 seconds
Command Timeout: 5 seconds
Retry Attempts: 3
Status Update Interval: 10 seconds
```

### Network Configuration

#### WiFi Settings (ESP8266)
```
SSID: Your network name
Password: Your network password
IP Assignment: DHCP or Static
Connection Timeout: 30 seconds
```

#### Server Settings
```
Server IP: Raspberry Pi IP address
API Port: 5000 (default)
WebSocket Port: 5000 (default)
SSL/HTTPS: Optional
```

### Performance Tuning

#### Resource Allocation
- **CPU Priority**: Adjust process priorities
- **Memory Limits**: Set memory usage limits
- **Disk Space**: Configure storage quotas
- **Network Bandwidth**: Limit network usage

#### Quality vs Performance
- **High Quality**: Better detection accuracy, slower processing
- **Balanced**: Good accuracy with reasonable speed
- **High Performance**: Faster processing, reduced accuracy

## Troubleshooting

### Common Issues

#### Video Upload Problems

**Issue**: Video upload fails
**Solutions**:
1. Check file format (MP4, AVI, MOV, WebM only)
2. Verify file size (under 500MB)
3. Check network connection
4. Try a different browser

**Issue**: Processing takes too long
**Solutions**:
1. Reduce video resolution
2. Shorten video length
3. Lower processing quality
4. Check system resources

#### Camera Issues

**Issue**: Camera not detected
**Solutions**:
1. Check camera connection
2. Verify camera permissions
3. Try different USB port
4. Restart camera service

**Issue**: Poor video quality
**Solutions**:
1. Clean camera lens
2. Adjust lighting conditions
3. Increase resolution settings
4. Check camera focus

#### Hardware Control Issues

**Issue**: Devices not discovered
**Solutions**:
1. Check WiFi connection
2. Verify device power
3. Confirm network settings
4. Restart device discovery

**Issue**: Commands not responding
**Solutions**:
1. Check device status
2. Verify network connectivity
3. Restart affected devices
4. Check command syntax

### Performance Issues

#### Slow System Response

**Symptoms**: Web interface slow to load
**Solutions**:
1. Check system resources (CPU, memory)
2. Clear browser cache
3. Restart web server
4. Optimize system settings

**Symptoms**: Video processing slow
**Solutions**:
1. Reduce video quality settings
2. Close unnecessary applications
3. Check available disk space
4. Monitor system temperature

#### Network Problems

**Symptoms**: Devices frequently disconnecting
**Solutions**:
1. Check WiFi signal strength
2. Verify network stability
3. Adjust device timeout settings
4. Consider network infrastructure

### Error Messages

#### Common Error Codes

**Error 404**: Resource not found
- Check URL spelling
- Verify service is running
- Confirm network connectivity

**Error 500**: Internal server error
- Check system logs
- Verify configuration
- Restart services if needed

**Error 413**: File too large
- Reduce video file size
- Check upload limits
- Compress video if possible

## Best Practices

### System Operation

#### Daily Operations
1. **Check System Status**: Review health dashboard
2. **Monitor Alerts**: Address any active alerts
3. **Review Logs**: Check for unusual activity
4. **Test Hardware**: Verify device connectivity

#### Weekly Maintenance
1. **Clean Camera Lenses**: Ensure clear video quality
2. **Check Disk Space**: Monitor storage usage
3. **Review Performance**: Analyze system metrics
4. **Update Device Status**: Verify all devices online

#### Monthly Tasks
1. **System Updates**: Apply security patches
2. **Log Rotation**: Archive old log files
3. **Performance Review**: Analyze trends
4. **Backup Configuration**: Save system settings

### Optimization Tips

#### Video Analysis
- Use appropriate video resolution for your needs
- Process shorter video segments for faster results
- Adjust detection sensitivity based on environment
- Regular lighting conditions improve accuracy

#### Live Monitoring
- Position cameras to minimize false positives
- Ensure adequate lighting for detection
- Use multiple cameras for comprehensive coverage
- Configure appropriate alert thresholds

#### Hardware Control
- Test devices regularly to ensure functionality
- Use descriptive device names for easy identification
- Configure appropriate response delays
- Monitor device battery levels (if applicable)

### Security Recommendations

#### Network Security
- Use strong WiFi passwords
- Enable network encryption (WPA2/WPA3)
- Regularly update device firmware
- Monitor network access logs

#### System Security
- Change default passwords
- Enable firewall protection
- Regular security updates
- Monitor system access

#### Data Protection
- Regular backup of configuration
- Secure storage of video files
- Privacy considerations for camera placement
- Data retention policies

### Performance Optimization

#### System Resources
- Monitor CPU and memory usage
- Optimize video processing settings
- Regular system maintenance
- Adequate cooling for hardware

#### Network Performance
- Use wired connections when possible
- Optimize WiFi signal strength
- Monitor network bandwidth usage
- Consider network infrastructure upgrades

This user guide provides comprehensive instructions for operating and maintaining the collision detection system effectively.