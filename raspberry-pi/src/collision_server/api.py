"""
REST API endpoints for the Collision Detection Server
"""
import os
import uuid
import base64
import cv2
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

from .video_processor import VideoProcessor
from .utils import allowed_file, get_file_extension


# Global video processor instance
video_processor = None


def init_video_processor(upload_folder: str, frame_callback=None):
    """Initialize the global video processor instance"""
    global video_processor
    video_processor = VideoProcessor(upload_folder, enable_collision_detection=True, frame_callback=frame_callback)


def create_api_blueprint(hardware_controller=None, status_monitor=None):
    """Create and configure the API blueprint"""
    api = Blueprint('api', __name__)
    
    @api.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'collision-detection-server',
            'version': '1.0.0',
            'collision_detection_enabled': video_processor.enable_collision_detection if video_processor else False
        })
    
    @api.route('/upload', methods=['POST'])
    def upload_video():
        """Upload video file for processing"""
        try:
            if 'video' not in request.files:
                return jsonify({'error': 'No video file provided'}), 400
            
            file = request.files['video']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({
                    'error': 'Invalid file format. Supported formats: MP4, AVI, MOV, WebM'
                }), 400
            
            # Generate unique filename
            filename = secure_filename(file.filename)
            file_extension = get_file_extension(filename)
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Save file
            upload_folder = current_app.config['UPLOAD_FOLDER']
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)
            
            # Create processing job
            job_id = str(uuid.uuid4())
            if video_processor:
                job = video_processor.create_processing_job(job_id, file_path)
                if not job:
                    return jsonify({'error': 'Failed to create processing job. Invalid video file.'}), 400
            
            return jsonify({
                'job_id': job_id,
                'filename': unique_filename,
                'original_filename': filename,
                'status': 'uploaded',
                'message': 'Video uploaded successfully. Use /process endpoint to start processing.'
            }), 201
            
        except RequestEntityTooLarge:
            return jsonify({'error': 'File too large. Maximum size is 500MB'}), 413
        except Exception as e:
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500
    
    @api.route('/process/<job_id>', methods=['POST'])
    def start_processing(job_id):
        """Start video processing for uploaded file"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            success = video_processor.start_processing(job_id)
            if not success:
                return jsonify({'error': 'Failed to start processing. Job not found or already processing.'}), 400
            
            return jsonify({
                'job_id': job_id,
                'status': 'processing_started',
                'message': 'Video processing started with collision detection'
            })
        except Exception as e:
            return jsonify({'error': f'Processing failed: {str(e)}'}), 500
    
    @api.route('/status/<job_id>', methods=['GET'])
    def get_processing_status(job_id):
        """Get processing status for a job"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            status = video_processor.get_processing_status(job_id)
            if not status:
                return jsonify({'error': 'Job not found'}), 404
            
            return jsonify(status)
        except Exception as e:
            return jsonify({'error': f'Status check failed: {str(e)}'}), 500
    
    @api.route('/results/<job_id>', methods=['GET'])
    def get_results(job_id):
        """Get processing results for a completed job"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            status = video_processor.get_processing_status(job_id)
            if not status:
                return jsonify({'error': 'Job not found'}), 404
            
            if status['status'] != 'completed':
                return jsonify({
                    'error': f'Job not completed. Current status: {status["status"]}'
                }), 400
            
            return jsonify({
                'job_id': job_id,
                'status': status['status'],
                'results': status.get('results', {}),
                'video_metadata': status.get('video_metadata', {})
            })
        except Exception as e:
            return jsonify({'error': f'Results retrieval failed: {str(e)}'}), 500
    
    @api.route('/collisions/<job_id>', methods=['GET'])
    def get_collision_results(job_id):
        """Get collision detection results for a completed job"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            collision_results = video_processor.get_collision_results(job_id)
            if not collision_results:
                return jsonify({'error': 'Job not found or collision results not available'}), 404
            
            return jsonify({
                'job_id': job_id,
                'collision_results': collision_results
            })
        except Exception as e:
            return jsonify({'error': f'Collision results retrieval failed: {str(e)}'}), 500
    
    @api.route('/jobs', methods=['GET'])
    def list_all_jobs():
        """List all processing jobs"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            jobs = video_processor.get_all_jobs()
            return jsonify({
                'jobs': jobs,
                'total_jobs': len(jobs)
            })
        except Exception as e:
            return jsonify({'error': f'Job listing failed: {str(e)}'}), 500
    
    @api.route('/settings/collision', methods=['POST'])
    def update_collision_settings():
        """Update collision detection settings"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            collision_threshold = request.json.get('collision_threshold')
            severity_threshold = request.json.get('severity_threshold')
            
            video_processor.set_collision_thresholds(collision_threshold, severity_threshold)
            
            return jsonify({
                'message': 'Collision detection settings updated',
                'collision_threshold': collision_threshold,
                'severity_threshold': severity_threshold
            })
        except Exception as e:
            return jsonify({'error': f'Settings update failed: {str(e)}'}), 500
    
    @api.route('/cameras', methods=['GET'])
    def get_cameras():
        """Get list of available cameras (alias for /camera/available)"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            available_cameras = video_processor.get_available_cameras()
            management_status = video_processor.get_camera_management_status()
            
            return jsonify({
                'available_cameras': available_cameras,
                'total_available': len(available_cameras),
                'camera_details': management_status.get('camera_details', {}),
                'active_cameras': management_status.get('active_cameras', [])
            })
        except Exception as e:
            return jsonify({'error': f'Camera listing failed: {str(e)}'}), 500
    
    @api.route('/camera/<int:camera_id>/start', methods=['POST'])
    def start_specific_camera(camera_id):
        """Start specific camera feed"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            success = video_processor.start_camera_feed(camera_id)
            
            if success:
                status = video_processor.get_camera_status(camera_id)
                return jsonify({
                    'camera_id': camera_id,
                    'status': 'started',
                    'message': f'Camera {camera_id} feed processing started',
                    'camera_info': status
                })
            else:
                return jsonify({
                    'error': f'Failed to start camera {camera_id}. Camera may not be available or already in use.'
                }), 400
        except Exception as e:
            return jsonify({'error': f'Camera start failed: {str(e)}'}), 500
    
    @api.route('/camera/<int:camera_id>/stop', methods=['POST'])
    def stop_specific_camera(camera_id):
        """Stop specific camera feed"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            success = video_processor.stop_camera_feed(camera_id)
            
            if success:
                return jsonify({
                    'camera_id': camera_id,
                    'status': 'stopped',
                    'message': f'Camera {camera_id} feed stopped'
                })
            else:
                return jsonify({
                    'error': f'Failed to stop camera {camera_id}. Camera may not be running.'
                }), 400
        except Exception as e:
            return jsonify({'error': f'Camera stop failed: {str(e)}'}), 500
    
    @api.route('/camera/start', methods=['POST'])
    def start_camera_feed():
        """Start real-time camera feed processing"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            camera_id = request.json.get('camera_id', 0) if request.json else 0
            
            success = video_processor.start_camera_feed(camera_id)
            
            if success:
                status = video_processor.get_camera_status(camera_id)
                return jsonify({
                    'camera_id': camera_id,
                    'status': 'started',
                    'message': 'Camera feed processing started',
                    'camera_info': status
                })
            else:
                return jsonify({
                    'error': f'Failed to start camera {camera_id}. Camera may not be available or already in use.'
                }), 400
        except Exception as e:
            return jsonify({'error': f'Camera start failed: {str(e)}'}), 500
    
    @api.route('/camera/stop', methods=['POST'])
    def stop_camera_feed():
        """Stop real-time camera feed processing"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            camera_id = request.json.get('camera_id', 0) if request.json else 0
            
            success = video_processor.stop_camera_feed(camera_id)
            
            if success:
                return jsonify({
                    'camera_id': camera_id,
                    'status': 'stopped',
                    'message': 'Camera feed stopped'
                })
            else:
                return jsonify({
                    'error': f'Failed to stop camera {camera_id}. Camera may not be running.'
                }), 400
        except Exception as e:
            return jsonify({'error': f'Camera stop failed: {str(e)}'}), 500
    
    @api.route('/camera/status', methods=['GET'])
    def get_camera_feeds_status():
        """Get status of all camera feeds"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            feeds = video_processor.get_all_camera_feeds()
            return jsonify({
                'camera_feeds': feeds,
                'total_cameras': len(feeds)
            })
        except Exception as e:
            return jsonify({'error': f'Camera status failed: {str(e)}'}), 500
    
    @api.route('/camera/status/<int:camera_id>', methods=['GET'])
    def get_camera_status(camera_id):
        """Get status of specific camera feed"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            status = video_processor.get_camera_status(camera_id)
            if not status:
                return jsonify({'error': f'Camera {camera_id} not found'}), 404
            
            return jsonify(status)
        except Exception as e:
            return jsonify({'error': f'Camera status failed: {str(e)}'}), 500
    
    @api.route('/camera/available', methods=['GET'])
    def get_available_cameras():
        """Get list of available camera devices"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            available_cameras = video_processor.get_available_cameras()
            return jsonify({
                'available_cameras': available_cameras,
                'total_available': len(available_cameras)
            })
        except Exception as e:
            return jsonify({'error': f'Camera detection failed: {str(e)}'}), 500
    
    @api.route('/camera/capture/<int:camera_id>', methods=['POST'])
    def capture_camera_frame(camera_id):
        """Capture a single frame from camera"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            frame = video_processor.capture_frame(camera_id)
            if frame is None:
                return jsonify({'error': f'Failed to capture frame from camera {camera_id}'}), 400
            
            # Encode frame as base64 JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_data = base64.b64encode(buffer).decode('utf-8')
            
            return jsonify({
                'camera_id': camera_id,
                'frame_data': frame_data,
                'timestamp': datetime.utcnow().isoformat(),
                'format': 'jpeg_base64'
            })
        except Exception as e:
            return jsonify({'error': f'Frame capture failed: {str(e)}'}), 500
    
    @api.route('/camera/alerts', methods=['GET'])
    def get_collision_alerts():
        """Get collision alerts from camera feeds"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            camera_id = request.args.get('camera_id', type=int)
            limit = request.args.get('limit', 50, type=int)
            
            alerts = video_processor.get_collision_alerts(camera_id, limit)
            
            return jsonify({
                'alerts': alerts,
                'total_alerts': len(alerts),
                'camera_id': camera_id,
                'limit': limit
            })
        except Exception as e:
            return jsonify({'error': f'Alert retrieval failed: {str(e)}'}), 500
    
    @api.route('/camera/alerts', methods=['DELETE'])
    def clear_collision_alerts():
        """Clear collision alerts from camera feeds"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            camera_id = request.args.get('camera_id', type=int)
            
            success = video_processor.clear_collision_alerts(camera_id)
            
            return jsonify({
                'success': success,
                'camera_id': camera_id,
                'message': f'Alerts cleared for {"all cameras" if camera_id is None else f"camera {camera_id}"}'
            })
        except Exception as e:
            return jsonify({'error': f'Alert clearing failed: {str(e)}'}), 500
    
    @api.route('/camera/start-all', methods=['POST'])
    def start_all_cameras():
        """Start all available camera feeds"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            results = video_processor.start_all_available_cameras()
            
            successful_cameras = [cam_id for cam_id, success in results.items() if success]
            failed_cameras = [cam_id for cam_id, success in results.items() if not success]
            
            return jsonify({
                'results': results,
                'successful_cameras': successful_cameras,
                'failed_cameras': failed_cameras,
                'total_started': len(successful_cameras),
                'message': f'Started {len(successful_cameras)} cameras successfully'
            })
        except Exception as e:
            return jsonify({'error': f'Start all cameras failed: {str(e)}'}), 500
    
    @api.route('/camera/stop-all', methods=['POST'])
    def stop_all_cameras():
        """Stop all active camera feeds"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            results = video_processor.stop_all_cameras()
            
            successful_stops = [cam_id for cam_id, success in results.items() if success]
            failed_stops = [cam_id for cam_id, success in results.items() if not success]
            
            return jsonify({
                'results': results,
                'successful_stops': successful_stops,
                'failed_stops': failed_stops,
                'total_stopped': len(successful_stops),
                'message': f'Stopped {len(successful_stops)} cameras successfully'
            })
        except Exception as e:
            return jsonify({'error': f'Stop all cameras failed: {str(e)}'}), 500
    
    @api.route('/camera/management', methods=['GET'])
    def get_camera_management():
        """Get comprehensive camera management status"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            management_status = video_processor.get_camera_management_status()
            
            return jsonify(management_status)
        except Exception as e:
            return jsonify({'error': f'Camera management status failed: {str(e)}'}), 500
    
    @api.route('/camera/switch', methods=['POST'])
    def switch_camera():
        """Switch from one camera feed to another"""
        try:
            if not video_processor:
                return jsonify({'error': 'Video processor not initialized'}), 500
            
            from_camera_id = request.json.get('from_camera_id')
            to_camera_id = request.json.get('to_camera_id')
            
            if from_camera_id is None or to_camera_id is None:
                return jsonify({'error': 'from_camera_id and to_camera_id are required'}), 400
            
            success = video_processor.switch_camera_feed(from_camera_id, to_camera_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'from_camera_id': from_camera_id,
                    'to_camera_id': to_camera_id,
                    'message': f'Successfully switched from camera {from_camera_id} to camera {to_camera_id}'
                })
            else:
                return jsonify({
                    'error': f'Failed to switch from camera {from_camera_id} to camera {to_camera_id}'
                }), 400
        except Exception as e:
            return jsonify({'error': f'Camera switch failed: {str(e)}'}), 500
    
    @api.route('/hardware/devices', methods=['GET'])
    def list_hardware_devices():
        """List connected ESP8266 devices"""
        try:
            if not hardware_controller:
                return jsonify({'error': 'Hardware controller not initialized'}), 500
            
            devices = hardware_controller.get_registered_devices()
            device_list = []
            
            for device_id, device_info in devices.items():
                device_data = {
                    'device_id': device_info.device_id,
                    'ip_address': device_info.ip_address,
                    'device_type': device_info.device_type,
                    'capabilities': device_info.capabilities,
                    'status': device_info.status,
                    'last_seen': device_info.last_seen
                }
                
                # Add health metrics if available
                if status_monitor:
                    health = status_monitor.get_device_health(device_id)
                    if health:
                        device_data['health'] = {
                            'overall_health': health.overall_health,
                            'connectivity_score': health.connectivity_score,
                            'performance_score': health.performance_score,
                            'error_count': health.error_count
                        }
                
                device_list.append(device_data)
            
            return jsonify({
                'devices': device_list,
                'total_devices': len(device_list)
            })
        except Exception as e:
            return jsonify({'error': f'Device listing failed: {str(e)}'}), 500
    
    @api.route('/hardware/command', methods=['POST'])
    def send_hardware_command():
        """Send command to ESP8266 device"""
        try:
            if not hardware_controller:
                return jsonify({'error': 'Hardware controller not initialized'}), 500
            
            device_id = request.json.get('device_id')
            command = request.json.get('command')
            parameters = request.json.get('parameters', {})
            
            if not device_id or not command:
                return jsonify({'error': 'device_id and command are required'}), 400
            
            success = hardware_controller.send_command(device_id, command, parameters)
            
            if success:
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
        except Exception as e:
            return jsonify({'error': f'Command failed: {str(e)}'}), 500
    
    @api.route('/hardware/broadcast', methods=['POST'])
    def broadcast_hardware_alert():
        """Broadcast alert to all ESP8266 devices"""
        try:
            if not hardware_controller:
                return jsonify({'error': 'Hardware controller not initialized'}), 500
            
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
        except Exception as e:
            return jsonify({'error': f'Broadcast failed: {str(e)}'}), 500
    
    @api.route('/hardware/status/<device_id>', methods=['GET'])
    def get_device_status(device_id):
        """Get detailed status for a specific device"""
        try:
            if not hardware_controller:
                return jsonify({'error': 'Hardware controller not initialized'}), 500
            
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
                'timestamp': device_status.timestamp
            }
            
            # Add health metrics if available
            if status_monitor:
                health = status_monitor.get_device_health(device_id)
                if health:
                    response_data['health_metrics'] = {
                        'overall_health': health.overall_health,
                        'connectivity_score': health.connectivity_score,
                        'performance_score': health.performance_score,
                        'error_count': health.error_count,
                        'last_error_time': health.last_error_time
                    }
                
                # Add status history
                status_history = status_monitor.get_device_status_history(device_id, limit=10)
                response_data['status_history'] = status_history
            
            return jsonify(response_data)
        except Exception as e:
            return jsonify({'error': f'Status retrieval failed: {str(e)}'}), 500
    
    @api.route('/hardware/logs/<device_id>', methods=['GET'])
    def get_device_logs(device_id):
        """Get command and event logs for a specific device"""
        try:
            if not hardware_controller:
                return jsonify({'error': 'Hardware controller not initialized'}), 500
            
            limit = request.args.get('limit', 50, type=int)
            
            # Get command logs
            command_logs = hardware_controller.get_detailed_command_log(device_id=device_id, limit=limit)
            
            # Get device event logs
            device_logs = hardware_controller.get_device_event_log(device_id=device_id, limit=limit)
            
            return jsonify({
                'device_id': device_id,
                'command_logs': command_logs,
                'device_logs': device_logs,
                'total_command_logs': len(command_logs),
                'total_device_logs': len(device_logs)
            })
        except Exception as e:
            return jsonify({'error': f'Log retrieval failed: {str(e)}'}), 500
    
    @api.route('/hardware/statistics', methods=['GET'])
    def get_hardware_statistics():
        """Get hardware system statistics"""
        try:
            if not hardware_controller:
                return jsonify({'error': 'Hardware controller not initialized'}), 500
            
            device_id = request.args.get('device_id')
            
            # Get command statistics
            stats = hardware_controller.get_command_statistics(device_id)
            
            response_data = {
                'command_statistics': stats
            }
            
            # Add system health if status monitor available
            if status_monitor:
                system_health = status_monitor.get_system_health()
                response_data['system_health'] = {
                    'total_devices': system_health.total_devices,
                    'online_devices': system_health.online_devices,
                    'offline_devices': system_health.offline_devices,
                    'error_devices': system_health.error_devices,
                    'average_response_time': system_health.average_response_time,
                    'system_uptime': system_health.system_uptime,
                    'cpu_usage': system_health.cpu_usage,
                    'memory_usage': system_health.memory_usage,
                    'network_status': system_health.network_status,
                    'timestamp': system_health.timestamp
                }
                
                # Add alert summary
                alerts = status_monitor.get_alert_summary()
                response_data['alerts'] = alerts
            
            return jsonify(response_data)
        except Exception as e:
            return jsonify({'error': f'Statistics retrieval failed: {str(e)}'}), 500
    
    @api.route('/hardware/discover', methods=['POST'])
    def discover_devices():
        """Trigger device discovery"""
        try:
            if not hardware_controller:
                return jsonify({'error': 'Hardware controller not initialized'}), 500
            
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
        except Exception as e:
            return jsonify({'error': f'Device discovery failed: {str(e)}'}), 500
    
    @api.route('/system/health', methods=['GET'])
    def get_system_health():
        """Get comprehensive system health information"""
        try:
            # Import here to avoid circular imports
            from .main import current_app
            system_monitor = current_app.config.get('SYSTEM_MONITOR')
            
            if not system_monitor:
                return jsonify({'error': 'System monitor not initialized'}), 500
            
            health_summary = system_monitor.get_system_health_summary()
            return jsonify(health_summary)
        except Exception as e:
            return jsonify({'error': f'Health check failed: {str(e)}'}), 500
    
    @api.route('/system/metrics', methods=['GET'])
    def get_system_metrics():
        """Get system performance metrics history"""
        try:
            from .main import current_app
            system_monitor = current_app.config.get('SYSTEM_MONITOR')
            
            if not system_monitor:
                return jsonify({'error': 'System monitor not initialized'}), 500
            
            duration = request.args.get('duration', 60, type=int)  # minutes
            metrics = system_monitor.get_performance_history(duration)
            
            return jsonify({
                'metrics': metrics,
                'duration_minutes': duration,
                'total_samples': len(metrics)
            })
        except Exception as e:
            return jsonify({'error': f'Metrics retrieval failed: {str(e)}'}), 500
    
    @api.route('/system/alerts', methods=['GET'])
    def get_system_alerts():
        """Get system alerts"""
        try:
            from .main import current_app
            system_monitor = current_app.config.get('SYSTEM_MONITOR')
            
            if not system_monitor:
                return jsonify({'error': 'System monitor not initialized'}), 500
            
            limit = request.args.get('limit', 50, type=int)
            alerts = system_monitor.get_alert_history(limit)
            
            return jsonify({
                'alerts': alerts,
                'total_alerts': len(alerts)
            })
        except Exception as e:
            return jsonify({'error': f'Alert retrieval failed: {str(e)}'}), 500
    
    @api.route('/system/alerts/<alert_id>', methods=['DELETE'])
    def resolve_alert(alert_id):
        """Resolve a specific alert"""
        try:
            from .main import current_app
            system_monitor = current_app.config.get('SYSTEM_MONITOR')
            
            if not system_monitor:
                return jsonify({'error': 'System monitor not initialized'}), 500
            
            success = system_monitor.resolve_alert(alert_id)
            
            if success:
                return jsonify({
                    'alert_id': alert_id,
                    'status': 'resolved',
                    'message': 'Alert resolved successfully'
                })
            else:
                return jsonify({'error': 'Alert not found or already resolved'}), 404
        except Exception as e:
            return jsonify({'error': f'Alert resolution failed: {str(e)}'}), 500
    
    @api.route('/system/logs', methods=['GET'])
    def get_system_logs():
        """Get system log files"""
        try:
            from .main import current_app
            system_monitor = current_app.config.get('SYSTEM_MONITOR')
            
            if not system_monitor:
                return jsonify({'error': 'System monitor not initialized'}), 500
            
            log_type = request.args.get('type', 'system')
            lines = request.args.get('lines', 100, type=int)
            
            log_lines = system_monitor.get_log_tail(log_type, lines)
            
            return jsonify({
                'log_type': log_type,
                'lines': log_lines,
                'total_lines': len(log_lines)
            })
        except Exception as e:
            return jsonify({'error': f'Log retrieval failed: {str(e)}'}), 500
    
    @api.route('/system/components', methods=['GET'])
    def get_component_status():
        """Get status of all system components"""
        try:
            from .main import current_app
            system_monitor = current_app.config.get('SYSTEM_MONITOR')
            
            if not system_monitor:
                return jsonify({'error': 'System monitor not initialized'}), 500
            
            health_summary = system_monitor.get_system_health_summary()
            
            return jsonify({
                'components': health_summary.get('component_health', {}),
                'overall_status': health_summary.get('overall_status', 'unknown')
            })
        except Exception as e:
            return jsonify({'error': f'Component status retrieval failed: {str(e)}'}), 500
    
    @api.route('/system/components/<component_name>', methods=['GET'])
    def get_component_details(component_name):
        """Get detailed information about a specific component"""
        try:
            from .main import current_app
            system_monitor = current_app.config.get('SYSTEM_MONITOR')
            
            if not system_monitor:
                return jsonify({'error': 'System monitor not initialized'}), 500
            
            component_metrics = system_monitor.get_component_metrics(component_name)
            
            if not component_metrics:
                return jsonify({'error': 'Component not found'}), 404
            
            return jsonify(component_metrics)
        except Exception as e:
            return jsonify({'error': f'Component details retrieval failed: {str(e)}'}), 500
    
    return api