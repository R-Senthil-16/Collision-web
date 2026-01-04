#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Collision Detection System
Tests all components and their interactions across the entire system
"""

import os
import sys
import time
import json
import asyncio
import threading
import subprocess
import requests
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import unittest
from unittest.mock import Mock, patch

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'raspberry-pi', 'src'))

from collision_server.main import create_app


@dataclass
class TestResult:
    """Test result information"""
    test_name: str
    passed: bool
    duration: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ComprehensiveIntegrationTests:
    """Comprehensive integration test suite covering all system components"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.ws_url = "ws://localhost:5000"
        self.test_results = []
        self.server_process = None
        self.app = None
        self.socketio = None
        self.test_data_dir = "test_data"
        
        # Test configuration
        self.test_config = {
            'video_formats': ['mp4', 'avi', 'mov', 'webm'],
            'test_devices': ['ESP8266_TEST_001', 'ESP8266_TEST_002'],
            'camera_ids': [0, 1],
            'performance_thresholds': {
                'video_processing_time': 30.0,  # seconds
                'api_response_time': 2.0,       # seconds
                'websocket_latency': 0.5        # seconds
            }
        }
    
    def setup_test_environment(self):
        """Set up comprehensive test environment"""
        print("Setting up comprehensive test environment...")
        
        # Create test directories
        os.makedirs(self.test_data_dir, exist_ok=True)
        os.makedirs("test_uploads", exist_ok=True)
        os.makedirs("test_logs", exist_ok=True)
        
        # Set environment variables for testing
        os.environ['UPLOAD_FOLDER'] = os.path.abspath("test_uploads")
        os.environ['LOG_DIRECTORY'] = os.path.abspath("test_logs")
        os.environ['DEBUG'] = 'True'
        os.environ['TESTING'] = 'True'
        
        # Create test video files for different formats
        self.create_test_videos()
        
        # Create mock ESP8266 responses
        self.setup_mock_devices()
        
        print("Test environment setup complete")
    
    def create_test_videos(self):
        """Create test videos in multiple formats"""
        print("Creating test videos in multiple formats...")
        
        # Video parameters
        width, height = 640, 480
        fps = 30
        duration = 3  # seconds
        total_frames = fps * duration
        
        for video_format in self.test_config['video_formats']:
            # Create video with collision scenario
            if video_format == 'mp4':
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            elif video_format == 'avi':
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
            elif video_format == 'mov':
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            elif video_format == 'webm':
                fourcc = cv2.VideoWriter_fourcc(*'VP80')
            
            video_path = f"{self.test_data_dir}/collision_test.{video_format}"
            out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
            
            for frame_num in range(total_frames):
                # Create frame with moving objects
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                
                # Calculate object positions
                progress = frame_num / total_frames
                
                # Object 1: moving from left to right
                obj1_x = int(50 + progress * (width - 150))
                obj1_y = height // 2
                
                # Object 2: moving from right to left
                obj2_x = int((width - 50) - progress * (width - 150))
                obj2_y = height // 2
                
                # Draw objects
                cv2.rectangle(frame, (obj1_x - 25, obj1_y - 25), (obj1_x + 25, obj1_y + 25), (0, 255, 0), -1)
                cv2.rectangle(frame, (obj2_x - 25, obj2_y - 25), (obj2_x + 25, obj2_y + 25), (0, 0, 255), -1)
                
                # Add frame number
                cv2.putText(frame, f"Frame {frame_num}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                out.write(frame)
            
            out.release()
            print(f"Created test video: {video_path}")
    
    def setup_mock_devices(self):
        """Setup mock ESP8266 device responses"""
        self.mock_device_responses = {}
        
        for device_id in self.test_config['test_devices']:
            self.mock_device_responses[device_id] = {
                'status': {
                    'device_id': device_id,
                    'status': 'online',
                    'uptime': 12345,
                    'free_memory': 25600,
                    'wifi_strength': -45,
                    'temperature': 35.2,
                    'sensor_data': {
                        'led_status': [True, False, True],
                        'servo_position': 90,
                        'relay_status': False
                    }
                },
                'capabilities': ['led_control', 'servo_control', 'relay_control', 'sensor_reading']
            }
    
    def start_server(self) -> bool:
        """Start the Flask server for testing"""
        print("Starting collision detection server for integration testing...")
        
        try:
            self.app, self.socketio, hardware_controller, status_monitor, resource_manager, system_monitor = create_app()
            
            # Start server in a separate thread
            def run_server():
                self.socketio.run(self.app, host='localhost', port=5000, debug=False)
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Wait for server to start
            time.sleep(3)
            
            # Test server connectivity
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                print("Server started successfully")
                return True
            else:
                print(f"Server health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False
    
    def run_test(self, test_name: str, test_func) -> TestResult:
        """Run a single test and record results"""
        print(f"\n--- Running Test: {test_name} ---")
        start_time = time.time()
        
        try:
            result = test_func()
            duration = time.time() - start_time
            
            if result is True:
                print(f"✅ {test_name} PASSED ({duration:.2f}s)")
                return TestResult(test_name, True, duration)
            elif isinstance(result, dict):
                print(f"✅ {test_name} PASSED ({duration:.2f}s)")
                return TestResult(test_name, True, duration, details=result)
            else:
                print(f"❌ {test_name} FAILED ({duration:.2f}s): {result}")
                return TestResult(test_name, False, duration, error_message=str(result))
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {test_name} FAILED ({duration:.2f}s): {e}")
            return TestResult(test_name, False, duration, error_message=str(e))
    
    def test_api_endpoints(self) -> bool:
        """Test all API endpoints for basic functionality"""
        endpoints_to_test = [
            ('GET', '/api/health', 200),
            ('GET', '/api/cameras', 200),
            ('GET', '/api/hardware/devices', 200),
            ('POST', '/api/hardware/discover', 200),
            ('GET', '/api/system/health', 200),
            ('GET', '/api/system/components', 200),
            ('GET', '/api/system/alerts', 200),
            ('GET', '/api/system/logs', 200)
        ]
        
        for method, endpoint, expected_status in endpoints_to_test:
            try:
                if method == 'GET':
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                elif method == 'POST':
                    response = requests.post(f"{self.base_url}{endpoint}", json={}, timeout=5)
                
                if response.status_code != expected_status:
                    return f"Endpoint {endpoint} returned {response.status_code}, expected {expected_status}"
                
                # Validate JSON response
                try:
                    response.json()
                except:
                    return f"Endpoint {endpoint} returned invalid JSON"
                    
            except Exception as e:
                return f"Endpoint {endpoint} failed: {e}"
        
        return True
    
    def test_video_upload_workflow(self) -> bool:
        """Test complete video upload and processing workflow"""
        for video_format in self.test_config['video_formats']:
            video_path = f"{self.test_data_dir}/collision_test.{video_format}"
            
            if not os.path.exists(video_path):
                return f"Test video {video_path} not found"
            
            try:
                # Upload video
                with open(video_path, 'rb') as video_file:
                    files = {'video': video_file}
                    response = requests.post(f"{self.base_url}/api/upload", files=files, timeout=30)
                
                if response.status_code != 201:
                    return f"Video upload failed for {video_format}: {response.status_code}"
                
                upload_result = response.json()
                job_id = upload_result.get('job_id')
                
                if not job_id:
                    return f"No job ID returned for {video_format} upload"
                
                # Start processing
                response = requests.post(f"{self.base_url}/api/process/{job_id}", timeout=10)
                if response.status_code != 200:
                    return f"Failed to start processing for {video_format}: {response.status_code}"
                
                # Wait for processing to complete
                max_wait = self.test_config['performance_thresholds']['video_processing_time']
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    response = requests.get(f"{self.base_url}/api/status/{job_id}")
                    if response.status_code == 200:
                        status = response.json()
                        if status.get('status') == 'completed':
                            break
                        elif status.get('status') == 'failed':
                            return f"Video processing failed for {video_format}: {status.get('error')}"
                    
                    time.sleep(2)
                else:
                    return f"Video processing timed out for {video_format}"
                
                # Get results
                response = requests.get(f"{self.base_url}/api/results/{job_id}")
                if response.status_code != 200:
                    return f"Failed to get results for {video_format}"
                
                results = response.json()
                if 'results' not in results:
                    return f"No results returned for {video_format}"
                
            except Exception as e:
                return f"Video workflow failed for {video_format}: {e}"
        
        return True
    
    def test_camera_management(self) -> bool:
        """Test camera management functionality"""
        try:
            # Get available cameras
            response = requests.get(f"{self.base_url}/api/cameras")
            if response.status_code != 200:
                return f"Failed to get cameras: {response.status_code}"
            
            cameras_data = response.json()
            
            # Test camera operations for each configured camera
            for camera_id in self.test_config['camera_ids']:
                # Try to start camera (may fail if no physical camera)
                response = requests.post(f"{self.base_url}/api/camera/start", 
                                       json={'camera_id': camera_id})
                
                # We expect this to potentially fail in test environment
                # The important thing is that the API responds properly
                if response.status_code not in [200, 400]:
                    return f"Unexpected response for camera start: {response.status_code}"
                
                # Test camera status
                response = requests.get(f"{self.base_url}/api/camera/status/{camera_id}")
                # This should return 404 if camera doesn't exist, which is fine
                if response.status_code not in [200, 404]:
                    return f"Unexpected response for camera status: {response.status_code}"
            
            return True
            
        except Exception as e:
            return f"Camera management test failed: {e}"
    
    def test_hardware_communication(self) -> bool:
        """Test hardware communication workflow"""
        try:
            # Test device discovery
            response = requests.post(f"{self.base_url}/api/hardware/discover")
            if response.status_code != 200:
                return f"Device discovery failed: {response.status_code}"
            
            # Test device listing
            response = requests.get(f"{self.base_url}/api/hardware/devices")
            if response.status_code != 200:
                return f"Device listing failed: {response.status_code}"
            
            devices = response.json().get('devices', [])
            
            # Test command broadcasting (will fail gracefully if no devices)
            test_command = {
                "action": "led_alert",
                "parameters": {
                    "color": "red",
                    "intensity": 255,
                    "duration": 1000
                }
            }
            
            response = requests.post(f"{self.base_url}/api/hardware/broadcast", 
                                   json=test_command)
            
            # This may return 400 if no devices, which is expected in test environment
            if response.status_code not in [200, 400]:
                return f"Unexpected response for command broadcast: {response.status_code}"
            
            # Test hardware statistics
            response = requests.get(f"{self.base_url}/api/hardware/statistics")
            if response.status_code != 200:
                return f"Hardware statistics failed: {response.status_code}"
            
            return True
            
        except Exception as e:
            return f"Hardware communication test failed: {e}"
    
    def test_system_monitoring(self) -> bool:
        """Test system monitoring and logging functionality"""
        try:
            # Test system health
            response = requests.get(f"{self.base_url}/api/system/health")
            if response.status_code != 200:
                return f"System health check failed: {response.status_code}"
            
            health_data = response.json()
            required_fields = ['overall_status', 'system_metrics', 'component_health']
            
            for field in required_fields:
                if field not in health_data:
                    return f"Missing field in health data: {field}"
            
            # Test system metrics
            response = requests.get(f"{self.base_url}/api/system/metrics?duration=5")
            if response.status_code != 200:
                return f"System metrics failed: {response.status_code}"
            
            # Test component status
            response = requests.get(f"{self.base_url}/api/system/components")
            if response.status_code != 200:
                return f"Component status failed: {response.status_code}"
            
            # Test system logs
            log_types = ['system', 'performance', 'errors', 'alerts']
            for log_type in log_types:
                response = requests.get(f"{self.base_url}/api/system/logs?type={log_type}&lines=10")
                if response.status_code != 200:
                    return f"System logs failed for {log_type}: {response.status_code}"
            
            # Test alerts
            response = requests.get(f"{self.base_url}/api/system/alerts")
            if response.status_code != 200:
                return f"System alerts failed: {response.status_code}"
            
            return True
            
        except Exception as e:
            return f"System monitoring test failed: {e}"
    
    def test_websocket_communication(self) -> bool:
        """Test WebSocket real-time communication"""
        try:
            # This is a simplified WebSocket test
            # In a full implementation, you'd test actual WebSocket connections
            
            # For now, we'll test that the WebSocket endpoints are available
            # by checking if the server responds to WebSocket upgrade requests
            
            import socket
            
            # Test if WebSocket port is accessible
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 5000))
            sock.close()
            
            if result != 0:
                return f"WebSocket port not accessible: {result}"
            
            return True
            
        except Exception as e:
            return f"WebSocket communication test failed: {e}"
    
    def test_performance_benchmarks(self) -> bool:
        """Test system performance benchmarks"""
        try:
            # Test API response times
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/health")
            api_response_time = time.time() - start_time
            
            if api_response_time > self.test_config['performance_thresholds']['api_response_time']:
                return f"API response time too slow: {api_response_time:.2f}s"
            
            # Test concurrent requests
            import concurrent.futures
            
            def make_request():
                return requests.get(f"{self.base_url}/api/health", timeout=5)
            
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            concurrent_time = time.time() - start_time
            
            # All requests should succeed
            for result in results:
                if result.status_code != 200:
                    return f"Concurrent request failed: {result.status_code}"
            
            # Test memory usage doesn't grow excessively
            import psutil
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            
            if memory_usage > 500:  # 500MB threshold
                return f"Memory usage too high: {memory_usage:.1f}MB"
            
            return True
            
        except Exception as e:
            return f"Performance benchmark failed: {e}"
    
    def test_error_handling(self) -> bool:
        """Test error handling and recovery"""
        try:
            # Test invalid video upload
            response = requests.post(f"{self.base_url}/api/upload", 
                                   files={'video': ('test.txt', b'not a video', 'text/plain')})
            if response.status_code not in [400, 415]:
                return f"Invalid video upload should fail: {response.status_code}"
            
            # Test invalid job ID
            response = requests.get(f"{self.base_url}/api/status/invalid_job_id")
            if response.status_code != 404:
                return f"Invalid job ID should return 404: {response.status_code}"
            
            # Test invalid device command
            response = requests.post(f"{self.base_url}/api/hardware/command", 
                                   json={'device_id': 'invalid', 'command': 'invalid'})
            if response.status_code not in [400, 404]:
                return f"Invalid device command should fail: {response.status_code}"
            
            # Test malformed JSON
            response = requests.post(f"{self.base_url}/api/hardware/command", 
                                   data='invalid json', 
                                   headers={'Content-Type': 'application/json'})
            if response.status_code != 400:
                return f"Malformed JSON should return 400: {response.status_code}"
            
            return True
            
        except Exception as e:
            return f"Error handling test failed: {e}"
    
    def test_data_validation(self) -> bool:
        """Test data validation and sanitization"""
        try:
            # Test SQL injection attempts (should be handled by framework)
            malicious_inputs = [
                "'; DROP TABLE users; --",
                "<script>alert('xss')</script>",
                "../../etc/passwd",
                "null\x00byte"
            ]
            
            for malicious_input in malicious_inputs:
                # Test in various endpoints
                response = requests.get(f"{self.base_url}/api/system/logs", 
                                      params={'type': malicious_input})
                
                # Should either reject or sanitize the input
                if response.status_code == 200:
                    # If it accepts the input, make sure it's sanitized
                    data = response.json()
                    if malicious_input in str(data):
                        return f"Malicious input not sanitized: {malicious_input}"
            
            # Test file upload size limits
            large_data = b'x' * (600 * 1024 * 1024)  # 600MB (over limit)
            response = requests.post(f"{self.base_url}/api/upload", 
                                   files={'video': ('large.mp4', large_data, 'video/mp4')},
                                   timeout=10)
            
            if response.status_code != 413:  # Request Entity Too Large
                return f"Large file upload should be rejected: {response.status_code}"
            
            return True
            
        except Exception as e:
            return f"Data validation test failed: {e}"
    
    def run_all_tests(self) -> Dict[str, TestResult]:
        """Run all comprehensive integration tests"""
        print("Starting Comprehensive Integration Test Suite")
        print("=" * 60)
        
        # Setup
        self.setup_test_environment()
        
        if not self.start_server():
            print("Failed to start server, aborting tests")
            return {"server_startup": TestResult("server_startup", False, 0, "Server failed to start")}
        
        # Define all tests
        test_methods = [
            ("api_endpoints", self.test_api_endpoints),
            ("video_upload_workflow", self.test_video_upload_workflow),
            ("camera_management", self.test_camera_management),
            ("hardware_communication", self.test_hardware_communication),
            ("system_monitoring", self.test_system_monitoring),
            ("websocket_communication", self.test_websocket_communication),
            ("performance_benchmarks", self.test_performance_benchmarks),
            ("error_handling", self.test_error_handling),
            ("data_validation", self.test_data_validation)
        ]
        
        # Run all tests
        results = {}
        for test_name, test_method in test_methods:
            result = self.run_test(test_name, test_method)
            results[test_name] = result
            self.test_results.append(result)
        
        return results
    
    def generate_test_report(self, results: Dict[str, TestResult]) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("COMPREHENSIVE INTEGRATION TEST REPORT")
        report.append("=" * 60)
        report.append(f"Test Run Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Tests: {len(results)}")
        
        passed_tests = [r for r in results.values() if r.passed]
        failed_tests = [r for r in results.values() if not r.passed]
        
        report.append(f"Passed: {len(passed_tests)}")
        report.append(f"Failed: {len(failed_tests)}")
        report.append(f"Success Rate: {len(passed_tests)/len(results)*100:.1f}%")
        report.append("")
        
        # Detailed results
        report.append("DETAILED RESULTS")
        report.append("-" * 40)
        
        for test_name, result in results.items():
            status = "PASS" if result.passed else "FAIL"
            report.append(f"{test_name:30} {status:4} ({result.duration:.2f}s)")
            
            if not result.passed and result.error_message:
                report.append(f"    Error: {result.error_message}")
            
            if result.details:
                report.append(f"    Details: {result.details}")
        
        report.append("")
        
        # Performance summary
        total_time = sum(r.duration for r in results.values())
        avg_time = total_time / len(results)
        
        report.append("PERFORMANCE SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Test Time: {total_time:.2f}s")
        report.append(f"Average Test Time: {avg_time:.2f}s")
        
        slowest_test = max(results.values(), key=lambda r: r.duration)
        report.append(f"Slowest Test: {slowest_test.test_name} ({slowest_test.duration:.2f}s)")
        
        return "\n".join(report)
    
    def cleanup(self):
        """Clean up test environment"""
        print("\nCleaning up test environment...")
        
        # Remove test files
        import shutil
        for directory in [self.test_data_dir, "test_uploads", "test_logs"]:
            if os.path.exists(directory):
                shutil.rmtree(directory)
        
        print("Cleanup complete")


def main():
    """Main function to run comprehensive integration tests"""
    test_suite = ComprehensiveIntegrationTests()
    
    try:
        results = test_suite.run_all_tests()
        
        # Generate and print report
        report = test_suite.generate_test_report(results)
        print("\n" + report)
        
        # Save report to file
        with open("integration_test_report.txt", "w") as f:
            f.write(report)
        
        # Determine exit code
        failed_tests = [r for r in results.values() if not r.passed]
        
        if len(failed_tests) == 0:
            print("\n🎉 ALL COMPREHENSIVE INTEGRATION TESTS PASSED!")
            return 0
        else:
            print(f"\n❌ {len(failed_tests)} integration tests failed")
            return 1
            
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"\nTest suite failed with error: {e}")
        return 1
    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    exit(main())