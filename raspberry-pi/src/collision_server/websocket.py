"""
WebSocket handlers for real-time communication
"""
from flask_socketio import emit, join_room, leave_room
from datetime import datetime


def setup_websocket_handlers(socketio, hardware_controller=None, status_monitor=None):
    """Setup WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print(f"Client connected at {datetime.utcnow().isoformat()}")
        emit('status', {
            'type': 'connection',
            'message': 'Connected to collision detection server',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f"Client disconnected at {datetime.utcnow().isoformat()}")
    
    @socketio.on('join_room')
    def handle_join_room(data):
        """Handle client joining a room for targeted updates"""
        room = data.get('room', 'general')
        join_room(room)
        emit('status', {
            'type': 'room_joined',
            'room': room,
            'message': f'Joined room: {room}',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('leave_room')
    def handle_leave_room(data):
        """Handle client leaving a room"""
        room = data.get('room', 'general')
        leave_room(room)
        emit('status', {
            'type': 'room_left',
            'room': room,
            'message': f'Left room: {room}',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('ping')
    def handle_ping():
        """Handle ping for connection testing"""
        emit('pong', {
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('hardware_command')
    def handle_hardware_command(data):
        """Handle hardware command from client"""
        if not hardware_controller:
            emit('error', {
                'type': 'hardware_error',
                'message': 'Hardware controller not available',
                'timestamp': datetime.utcnow().isoformat()
            })
            return
        
        device_id = data.get('device_id')
        command = data.get('command')
        parameters = data.get('parameters', {})
        
        if not device_id or not command:
            emit('error', {
                'type': 'validation_error',
                'message': 'device_id and command are required',
                'timestamp': datetime.utcnow().isoformat()
            })
            return
        
        success = hardware_controller.send_command(device_id, command, parameters)
        
        emit('hardware_command_result', {
            'type': 'command_result',
            'device_id': device_id,
            'command': command,
            'success': success,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('request_device_status')
    def handle_device_status_request(data):
        """Handle request for device status"""
        if not hardware_controller or not status_monitor:
            emit('error', {
                'type': 'service_error',
                'message': 'Hardware services not available',
                'timestamp': datetime.utcnow().isoformat()
            })
            return
        
        device_id = data.get('device_id')
        
        if device_id:
            # Get status for specific device
            device_status = hardware_controller.get_device_status(device_id)
            health_metrics = status_monitor.get_device_health(device_id)
            
            emit('device_status', {
                'type': 'device_status',
                'device_id': device_id,
                'status': device_status.__dict__ if device_status else None,
                'health': health_metrics.__dict__ if health_metrics else None,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            # Get status for all devices
            devices = hardware_controller.get_registered_devices()
            device_statuses = {}
            
            for dev_id in devices:
                device_status = hardware_controller.get_device_status(dev_id)
                health_metrics = status_monitor.get_device_health(dev_id)
                device_statuses[dev_id] = {
                    'status': device_status.__dict__ if device_status else None,
                    'health': health_metrics.__dict__ if health_metrics else None
                }
            
            emit('all_device_status', {
                'type': 'all_device_status',
                'devices': device_statuses,
                'timestamp': datetime.utcnow().isoformat()
            })
    
    @socketio.on('request_system_health')
    def handle_system_health_request():
        """Handle request for system health"""
        if not status_monitor:
            emit('error', {
                'type': 'service_error',
                'message': 'Status monitor not available',
                'timestamp': datetime.utcnow().isoformat()
            })
            return
        
        system_health = status_monitor.get_system_health()
        alerts = status_monitor.get_alert_summary()
        
        emit('system_health', {
            'type': 'system_health',
            'health': system_health.__dict__,
            'alerts': alerts,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('start_camera_stream')
    def handle_start_camera_stream(data):
        """Handle request to start camera streaming"""
        camera_id = data.get('camera_id', 0)
        room = f'camera_{camera_id}'
        
        # Join camera-specific room
        join_room(room)
        
        emit('camera_stream_started', {
            'type': 'camera_stream_started',
            'camera_id': camera_id,
            'room': room,
            'message': f'Started streaming camera {camera_id}',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('stop_camera_stream')
    def handle_stop_camera_stream(data):
        """Handle request to stop camera streaming"""
        camera_id = data.get('camera_id', 0)
        room = f'camera_{camera_id}'
        
        # Leave camera-specific room
        leave_room(room)
        
        emit('camera_stream_stopped', {
            'type': 'camera_stream_stopped',
            'camera_id': camera_id,
            'room': room,
            'message': f'Stopped streaming camera {camera_id}',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Real-time event emitters (to be called by other modules)
    def emit_collision_detected(collision_data, room='general'):
        """Emit collision detection event to clients"""
        socketio.emit('collision_detected', {
            'type': 'collision',
            'data': collision_data,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)
    
    def emit_processing_update(job_id, progress, status, room='general'):
        """Emit video processing progress update"""
        socketio.emit('processing_update', {
            'type': 'processing_progress',
            'job_id': job_id,
            'progress': progress,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)
    
    def emit_hardware_status(device_id, status, room='general'):
        """Emit hardware device status update"""
        socketio.emit('hardware_status', {
            'type': 'hardware_update',
            'device_id': device_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)
    
    def emit_camera_frame(camera_id, frame_data, metadata=None, room='general'):
        """Emit camera frame with optional collision detections"""
        # Send to general room and camera-specific room
        camera_room = f'camera_{camera_id}'
        
        frame_event = {
            'type': 'camera_frame',
            'camera_id': camera_id,
            'frame_data': frame_data,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        socketio.emit('camera_frame', frame_event, room=room)
        socketio.emit('camera_frame', frame_event, room=camera_room)
        
        # If this frame contains collision alerts, emit separate collision event
        if metadata and metadata.get('alert') and metadata.get('detections'):
            collision_event = {
                'type': 'real_time_collision',
                'camera_id': camera_id,
                'detections': metadata['detections'],
                'timestamp': datetime.utcnow().isoformat()
            }
            socketio.emit('collision_alert', collision_event, room=room)
            socketio.emit('collision_alert', collision_event, room=camera_room)
    
    # Store emitter functions in socketio instance for access by other modules
    socketio.emit_collision_detected = emit_collision_detected
    socketio.emit_processing_update = emit_processing_update
    socketio.emit_hardware_status = emit_hardware_status
    socketio.emit_camera_frame = emit_camera_frame
    
    # Setup status monitor callback if available
    if status_monitor:
        def status_update_callback(status_data):
            """Callback for status monitor updates"""
            socketio.emit('status_update', {
                'type': 'status_update',
                'data': status_data,
                'timestamp': datetime.utcnow().isoformat()
            }, room='general')
        
        status_monitor.add_status_callback(status_update_callback)