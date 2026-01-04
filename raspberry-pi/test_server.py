#!/usr/bin/env python3
"""
Test server for hardware interface development
Simplified version without computer vision dependencies
"""
import os
import time
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime


# Mock hardware controller for testing
class MockHardwareController:
    def __init__(self):
        self.devices = {
            'esp8266_001': {
                'device_id': 'esp8266_001',
                'ip_address': '192.168.1.100',
                'device_type': 'esp8266',
                'capabilities': ['led', 'servo', 'relay'],
                'status': 'online',
                'last_seen': time.time()
            },
            'esp8266_002': {
                'device_id': 'esp8266_002',
                'ip_address': '192.168.1.101',
                'device_type': 'esp8266',
                'capabilities': ['led', 'sensor'],
                'status': 'online',
                'last_seen': time.time()
            }
        }
        self.command_log = []
    
    def get_registered_devices(self):
        return {k: type('DeviceInfo', (), v)() for k, v in self.devices.items()}
    
    def send_command(self, device_id, command, parameters=None):
        if device_id in self.devices:
            self.command_log.append({
                'device_id': device_id,
                'command': command,
                'parameters': parameters or {},
                'timestamp': time.time(),
                'status': 'success'
            })
            print(f"Mock command sent to {device_id}: {command}")
            return True
        return False
    
    def get_device_status(self, device_id):
        if device_id in self.devices:
            device = self.devices[device_id]
            return type('DeviceStatus', (), {
                'device_id': device_id,
                'status': device['status'],
                'uptime': int(time.time() - device['last_seen'] + 3600),
                'free_memory': 32768,
                'wifi_strength': -45,
                'sensor_data': {'temperature': 23.5, 'humidity': 45.2},
                'timestamp': time.time()
            })()
        return None
    
    def broadcast_alert(self, message, alert_type='collision'):
        count = 0
        for device_id in self.devices:
            if self.send_command(device_id, 'alert', {'message': message, 'alert_type': alert_type}):
                count += 1
        return count
    
    def connect_devices(self):
        return len(self.devices) > 0
    
    def get_detailed_command_log(self, device_id=None, limit=None):
        logs = self.command_log
        if device_id:
            logs = [log for log in logs if log['device_id'] == device_id]
        if limit:
            logs = logs[-limit:]
        return logs
    
    def get_device_event_log(self, device_id=None, limit=None):
        # Mock device events
        events = [
            {
                'device_id': device_id or 'esp8266_001',
                'event_type': 'connection',
                'timestamp': time.time() - 3600,
                'severity': 'info'
            },
            {
                'device_id': device_id or 'esp8266_002',
                'event_type': 'connection',
                'timestamp': time.time() - 3500,
                'severity': 'info'
            }
        ]
        if device_id:
            events = [e for e in events if e['device_id'] == device_id]
        if limit:
            events = events[-limit:]
        return events
    
    def get_command_statistics(self, device_id=None):
        return {
            'total_commands': len(self.command_log),
            'successful_commands': len([c for c in self.command_log if c['status'] == 'success']),
            'failed_commands': 0,
            'average_response_time': 0.05
        }


# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key'
CORS(app, origins=["http://localhost:3000", "http://localhost:8080"])

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize mock hardware controller
hardware_controller = MockHardwareController()

# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'collision-detection-test-server',
        'version': '1.0.0'
    })

@app.route('/api/hardware/devices', methods=['GET'])
def list_hardware_devices():
    devices = hardware_controller.get_registered_devices()
    device_list = []
    
    for device_id, device_info in devices.items():
        device_data = {
            'device_id': device_info.device_id,
            'ip_address': device_info.ip_address,
            'device_type': device_info.device_type,
            'capabilities': device_info.capabilities,
            'status': device_info.status,
            'last_seen': device_info.last_seen,
            'health': {
                'overall_health': 0.95,
                'connectivity_score': 0.98,
                'performance_score': 0.92,
                'error_count': 0
            }
        }
        device_list.append(device_data)
    
    return jsonify({
        'devices': device_list,
        'total_devices': len(device_list)
    })

@app.route('/api/hardware/command', methods=['POST'])
def send_hardware_command():
    device_id = request.json.get('device_id')
    command = request.json.get('command')
    parameters = request.json.get('parameters', {})
    
    if not device_id or not command:
        return jsonify({'error': 'device_id and command are required'}), 400
    
    success = hardware_controller.send_command(device_id, command, parameters)
    
    if success:
        # Emit WebSocket event
        socketio.emit('hardware_command_result', {
            'type': 'command_result',
            'device_id': device_id,
            'command': command,
            'success': True,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            'device_id': device_id,
            'command': command,
            'parameters': parameters,
            'status': 'sent',
            'message': 'Command sent successfully'
        })
    else:
        return jsonify({
            'error': 'Failed to send command. Device may not be registered or reachable.'
        }), 400

@app.route('/api/hardware/broadcast', methods=['POST'])
def broadcast_hardware_alert():
    message = request.json.get('message')
    alert_type = request.json.get('alert_type', 'collision')
    
    if not message:
        return jsonify({'error': 'message is required'}), 400
    
    successful_count = hardware_controller.broadcast_alert(message, alert_type)
    
    return jsonify({
        'message': message,
        'alert_type': alert_type,
        'devices_notified': successful_count,
        'status': 'broadcast_complete'
    })

@app.route('/api/hardware/status/<device_id>', methods=['GET'])
def get_device_status(device_id):
    device_status = hardware_controller.get_device_status(device_id)
    if not device_status:
        return jsonify({'error': 'Device not found or unreachable'}), 404
    
    response_data = {
        'device_id': device_status.device_id,
        'status': device_status.status,
        'uptime': device_status.uptime,
        'free_memory': device_status.free_memory,
        'wifi_strength': device_status.wifi_strength,
        'sensor_data': device_status.sensor_data,
        'timestamp': device_status.timestamp,
        'health_metrics': {
            'overall_health': 0.95,
            'connectivity_score': 0.98,
            'performance_score': 0.92,
            'error_count': 0,
            'last_error_time': None
        }
    }
    
    return jsonify(response_data)

@app.route('/api/hardware/logs/<device_id>', methods=['GET'])
def get_device_logs(device_id):
    limit = request.args.get('limit', 50, type=int)
    
    command_logs = hardware_controller.get_detailed_command_log(device_id=device_id, limit=limit)
    device_logs = hardware_controller.get_device_event_log(device_id=device_id, limit=limit)
    
    return jsonify({
        'device_id': device_id,
        'command_logs': command_logs,
        'device_logs': device_logs,
        'total_command_logs': len(command_logs),
        'total_device_logs': len(device_logs)
    })

@app.route('/api/hardware/statistics', methods=['GET'])
def get_hardware_statistics():
    device_id = request.args.get('device_id')
    stats = hardware_controller.get_command_statistics(device_id)
    
    return jsonify({
        'command_statistics': stats,
        'system_health': {
            'total_devices': 2,
            'online_devices': 2,
            'offline_devices': 0,
            'error_devices': 0,
            'average_response_time': 0.05,
            'system_uptime': 3600,
            'cpu_usage': 25.5,
            'memory_usage': 45.2,
            'network_status': 'connected',
            'timestamp': time.time()
        }
    })

@app.route('/api/hardware/discover', methods=['POST'])
def discover_devices():
    success = hardware_controller.connect_devices()
    devices = hardware_controller.get_registered_devices()
    
    return jsonify({
        'discovery_successful': success,
        'devices_found': len(devices),
        'devices': [
            {
                'device_id': device.device_id,
                'ip_address': device.ip_address,
                'device_type': device.device_type,
                'status': device.status
            }
            for device in devices.values()
        ]
    })

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    print(f"Client connected at {datetime.utcnow().isoformat()}")
    emit('status', {
        'type': 'connection',
        'message': 'Connected to test server',
        'timestamp': datetime.utcnow().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected at {datetime.utcnow().isoformat()}")

@socketio.on('join_room')
def handle_join_room(data):
    from flask_socketio import join_room
    room = data.get('room', 'general')
    join_room(room)
    emit('status', {
        'type': 'room_joined',
        'room': room,
        'message': f'Joined room: {room}',
        'timestamp': datetime.utcnow().isoformat()
    })

@socketio.on('request_device_status')
def handle_device_status_request(data):
    device_id = data.get('device_id')
    
    if device_id:
        device_status = hardware_controller.get_device_status(device_id)
        emit('device_status', {
            'type': 'device_status',
            'device_id': device_id,
            'status': device_status.__dict__ if device_status else None,
            'timestamp': datetime.utcnow().isoformat()
        })
    else:
        devices = hardware_controller.get_registered_devices()
        device_statuses = {}
        
        for dev_id in devices:
            device_status = hardware_controller.get_device_status(dev_id)
            device_statuses[dev_id] = {
                'status': device_status.__dict__ if device_status else None
            }
        
        emit('all_device_status', {
            'type': 'all_device_status',
            'devices': device_statuses,
            'timestamp': datetime.utcnow().isoformat()
        })

if __name__ == '__main__':
    print("Starting Test Hardware Interface Server...")
    print("Server will run on http://localhost:5000")
    print("Hardware API available at http://localhost:5000/api/hardware/")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)