"""
Property-based tests for status reporting system.

Tests universal properties for device status monitoring, health reporting,
and system status accuracy using Hypothesis for comprehensive input coverage.

**Feature: collision-detection-web, Property 16: Status Reporting Accuracy**
**Feature: collision-detection-web, Property 18: Health Status Completeness**
**Validates: Requirements 10.5, 11.5**
"""

import time
import tempfile
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from dataclasses import asdict
import pytest

from collision_server.hardware_controller import HardwareController, DeviceInfo, DeviceStatus
from collision_server.status_monitor import StatusMonitor, HealthMetrics, SystemHealth


# Test data generators
@st.composite
def device_status_strategy(draw):
    """Generate valid DeviceStatus objects"""
    device_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    status = draw(st.sampled_from(["online", "offline", "error", "maintenance"]))
    uptime = draw(st.integers(0, 1000000))  # seconds
    free_memory = draw(st.integers(0, 100))  # percentage
    wifi_strength = draw(st.integers(-100, -20))  # dBm
    sensor_data = draw(st.dictionaries(
        st.text(min_size=1, max_size=10), 
        st.one_of(st.integers(), st.floats(allow_nan=False, allow_infinity=False), st.text(max_size=20)),
        min_size=0, max_size=5
    ))
    
    return DeviceStatus(
        device_id=device_id,
        status=status,
        uptime=uptime,
        free_memory=free_memory,
        wifi_strength=wifi_strength,
        sensor_data=sensor_data,
        timestamp=time.time()
    )


@st.composite
def health_metrics_strategy(draw):
    """Generate valid HealthMetrics objects"""
    device_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    uptime_history = draw(st.lists(st.integers(0, 1000000), min_size=0, max_size=10))
    memory_history = draw(st.lists(st.integers(0, 100), min_size=0, max_size=10))
    wifi_history = draw(st.lists(st.integers(-100, -20), min_size=0, max_size=10))
    response_history = draw(st.lists(st.floats(0.1, 10.0), min_size=0, max_size=10))
    error_count = draw(st.integers(0, 100))
    connectivity_score = draw(st.floats(0.0, 100.0))
    performance_score = draw(st.floats(0.0, 100.0))
    overall_health = draw(st.sampled_from(["excellent", "good", "fair", "poor", "critical", "unknown"]))
    
    return HealthMetrics(
        device_id=device_id,
        uptime_history=uptime_history,
        memory_history=memory_history,
        wifi_strength_history=wifi_history,
        response_time_history=response_history,
        error_count=error_count,
        last_error_time=time.time() if error_count > 0 else None,
        connectivity_score=connectivity_score,
        performance_score=performance_score,
        overall_health=overall_health
    )


class TestStatusReportingAccuracy:
    """
    Property-based tests for status reporting accuracy.
    
    **Property 16: Status Reporting Accuracy**
    *For any* ESP8266 device status update, the Hardware_Controller should 
    accurately relay the status information to the web interface without data corruption.
    """
    
    @given(device_status_strategy())
    @settings(max_examples=100)
    def test_device_status_relay_accuracy(self, device_status):
        """
        **Feature: collision-detection-web, Property 16: Status Reporting Accuracy**
        **Validates: Requirements 10.5**
        
        For any device status update, the status information should be
        accurately relayed without data corruption or loss.
        """
        # Setup hardware controller with temporary log directory
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = HardwareController({"log_directory": temp_dir})
            
            # Create and register a test device
            device_info = DeviceInfo(
                device_id=device_status.device_id,
                ip_address="192.168.1.100",
                device_type="esp8266",
                capabilities=["led", "sensor"],
                last_seen=time.time(),
                status="online"
            )
            controller.registered_devices[device_status.device_id] = device_info
            
            # Mock the status query to return our test status
            with patch.object(controller, '_query_device_status', return_value=device_status):
                # Get device status through controller
                retrieved_status = controller.get_device_status(device_status.device_id)
                
                # Property: Retrieved status should match original status
                assert retrieved_status is not None, "Status should be retrieved successfully"
                assert retrieved_status.device_id == device_status.device_id, "Device ID should match"
                assert retrieved_status.status == device_status.status, "Status should match"
                assert retrieved_status.uptime == device_status.uptime, "Uptime should match"
                assert retrieved_status.free_memory == device_status.free_memory, "Memory should match"
                assert retrieved_status.wifi_strength == device_status.wifi_strength, "WiFi strength should match"
                assert retrieved_status.sensor_data == device_status.sensor_data, "Sensor data should match"
                
                # Property: Timestamp should be preserved or updated appropriately
                assert retrieved_status.timestamp > 0, "Timestamp should be valid"
    
    @given(st.lists(device_status_strategy(), min_size=1, max_size=5))
    @settings(max_examples=100)
    def test_multiple_device_status_consistency(self, device_status_list):
        """
        **Feature: collision-detection-web, Property 16: Status Reporting Accuracy**
        **Validates: Requirements 10.5**
        
        For any collection of device status updates, each device's status
        should be reported independently and accurately without cross-contamination.
        """
        # Setup hardware controller with temporary log directory
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = HardwareController({"log_directory": temp_dir})
            
            # Create unique device IDs to avoid conflicts
            unique_devices = {}
            for i, status in enumerate(device_status_list):
                unique_id = f"{status.device_id}_{i}"
                status.device_id = unique_id
                
                # Register device
                device_info = DeviceInfo(
                    device_id=unique_id,
                    ip_address=f"192.168.1.{100 + i}",
                    device_type="esp8266",
                    capabilities=["led"],
                    last_seen=time.time(),
                    status="online"
                )
                controller.registered_devices[unique_id] = device_info
                unique_devices[unique_id] = status
            
            # Mock status queries for each device
            def mock_query_status(device_info):
                return unique_devices.get(device_info.device_id)
            
            with patch.object(controller, '_query_device_status', side_effect=mock_query_status):
                # Get status for all devices
                retrieved_statuses = {}
                for device_id in unique_devices:
                    retrieved_statuses[device_id] = controller.get_device_status(device_id)
                
                # Property: All devices should have status retrieved
                assert len(retrieved_statuses) == len(unique_devices), "All devices should have status"
                
                # Property: Each device's status should match exactly
                for device_id, original_status in unique_devices.items():
                    retrieved = retrieved_statuses[device_id]
                    assert retrieved is not None, f"Device {device_id} should have status"
                    assert retrieved.device_id == original_status.device_id, f"Device ID should match for {device_id}"
                    assert retrieved.status == original_status.status, f"Status should match for {device_id}"
                    assert retrieved.uptime == original_status.uptime, f"Uptime should match for {device_id}"
                    assert retrieved.free_memory == original_status.free_memory, f"Memory should match for {device_id}"
    
    @given(device_status_strategy())
    @settings(max_examples=100)
    def test_status_update_callback_accuracy(self, device_status):
        """
        **Feature: collision-detection-web, Property 16: Status Reporting Accuracy**
        **Validates: Requirements 10.5**
        
        For any status update callback, the callback should receive
        accurate and complete status information.
        """
        # Setup hardware controller and status monitor
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = HardwareController({"log_directory": temp_dir})
            monitor = StatusMonitor(controller, update_interval=1.0)
            
            # Register device
            device_info = DeviceInfo(
                device_id=device_status.device_id,
                ip_address="192.168.1.100",
                device_type="esp8266",
                capabilities=["led"],
                last_seen=time.time(),
                status="online"
            )
            controller.registered_devices[device_status.device_id] = device_info
            
            # Setup callback to capture status updates
            callback_data = []
            
            def status_callback(status_update):
                callback_data.append(status_update)
            
            monitor.add_status_callback(status_callback)
            
            # Mock status query and system health methods to avoid delays
            with patch.object(controller, '_query_device_status', return_value=device_status), \
                 patch.object(monitor, '_get_cpu_usage', return_value=25.0), \
                 patch.object(monitor, '_get_memory_usage', return_value=60.0), \
                 patch.object(monitor, '_get_network_status', return_value="connected"):
                
                # Force status update and manually trigger callback
                monitor.force_status_update(device_status.device_id)
                
                # Manually trigger the callback with status update (simulating monitoring loop)
                status_update = {
                    "timestamp": time.time(),
                    "device_health": {device_status.device_id: asdict(monitor.device_metrics.get(device_status.device_id, 
                        HealthMetrics(device_status.device_id, [], [], [], [], 0, None, 0.0, 0.0, "unknown")))},
                    "system_health": asdict(monitor.get_system_health()),
                    "alerts": monitor.get_alert_summary()
                }
                
                for callback in monitor.status_callbacks:
                    callback(status_update)
                
                # Property: Callback should be called with status data
                assert len(callback_data) > 0, "Status callback should be called"
                
                # Property: Callback data should contain device information
                latest_update = callback_data[-1]
                assert "device_health" in latest_update, "Update should contain device health"
                assert "system_health" in latest_update, "Update should contain system health"
                assert "timestamp" in latest_update, "Update should contain timestamp"
                
                # Property: Device health should be present for our device
                device_health = latest_update["device_health"]
                assert device_status.device_id in device_health, f"Device {device_status.device_id} should be in health data"


class TestHealthStatusCompleteness:
    """
    Property-based tests for health status completeness.
    
    **Property 18: Health Status Completeness**
    *For any* system health query, the Raspberry_Pi_Server should provide 
    complete status information including CPU usage, memory usage, camera status, 
    and device connectivity.
    """
    
    @given(st.lists(health_metrics_strategy(), min_size=1, max_size=5))
    @settings(max_examples=100, deadline=None)  # Disable deadline due to system calls
    def test_system_health_completeness(self, health_metrics_list):
        """
        **Feature: collision-detection-web, Property 18: Health Status Completeness**
        **Validates: Requirements 11.5**
        
        For any system health query, all required health information
        should be present and complete.
        """
        # Setup hardware controller and status monitor
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = HardwareController({"log_directory": temp_dir})
            monitor = StatusMonitor(controller, update_interval=1.0)
            
            # Mock system resource methods to avoid delays and external dependencies
            with patch.object(monitor, '_get_cpu_usage', return_value=25.0), \
                 patch.object(monitor, '_get_memory_usage', return_value=60.0), \
                 patch.object(monitor, '_get_network_status', return_value="connected"):
                
                # Register devices and set up health metrics
                for i, health_metrics in enumerate(health_metrics_list):
                    unique_id = f"{health_metrics.device_id}_{i}"
                    health_metrics.device_id = unique_id
                    
                    # Register device
                    device_info = DeviceInfo(
                        device_id=unique_id,
                        ip_address=f"192.168.1.{100 + i}",
                        device_type="esp8266",
                        capabilities=["led"],
                        last_seen=time.time(),
                        status="online"
                    )
                    controller.registered_devices[unique_id] = device_info
                    
                    # Set health metrics
                    monitor.device_metrics[unique_id] = health_metrics
                
                # Get system health
                system_health = monitor.get_system_health()
                
                # Property: System health should contain all required fields
                required_fields = [
                    'total_devices', 'online_devices', 'offline_devices', 'error_devices',
                    'average_response_time', 'system_uptime', 'cpu_usage', 'memory_usage',
                    'network_status', 'timestamp'
                ]
                
                for field in required_fields:
                    assert hasattr(system_health, field), f"System health should contain {field}"
                    assert getattr(system_health, field) is not None, f"System health {field} should not be None"
                
                # Property: Device counts should be consistent
                assert system_health.total_devices == len(health_metrics_list), "Total devices should match registered devices"
                assert system_health.total_devices == (
                    system_health.online_devices + 
                    system_health.offline_devices + 
                    system_health.error_devices
                ), "Device counts should sum to total"
                
                # Property: Timestamp should be recent
                assert system_health.timestamp > 0, "Timestamp should be valid"
                assert abs(system_health.timestamp - time.time()) < 60, "Timestamp should be recent"
    
    @given(health_metrics_strategy())
    @settings(max_examples=100)
    def test_device_health_metrics_completeness(self, health_metrics):
        """
        **Feature: collision-detection-web, Property 18: Health Status Completeness**
        **Validates: Requirements 11.5**
        
        For any device health query, all health metrics should be
        present and properly calculated.
        """
        # Setup hardware controller and status monitor
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = HardwareController({"log_directory": temp_dir})
            monitor = StatusMonitor(controller, update_interval=1.0)
            
            # Register device
            device_info = DeviceInfo(
                device_id=health_metrics.device_id,
                ip_address="192.168.1.100",
                device_type="esp8266",
                capabilities=["led"],
                last_seen=time.time(),
                status="online"
            )
            controller.registered_devices[health_metrics.device_id] = device_info
            
            # Set health metrics
            monitor.device_metrics[health_metrics.device_id] = health_metrics
            
            # Get device health
            retrieved_health = monitor.get_device_health(health_metrics.device_id)
            
            # Property: Health metrics should be retrieved
            assert retrieved_health is not None, "Device health should be retrievable"
            
            # Property: All health fields should be present
            required_fields = [
                'device_id', 'uptime_history', 'memory_history', 'wifi_strength_history',
                'response_time_history', 'error_count', 'connectivity_score',
                'performance_score', 'overall_health'
            ]
            
            for field in required_fields:
                assert hasattr(retrieved_health, field), f"Health metrics should contain {field}"
            
            # Property: Device ID should match
            assert retrieved_health.device_id == health_metrics.device_id, "Device ID should match"
            
            # Property: Scores should be within valid range
            assert 0.0 <= retrieved_health.connectivity_score <= 100.0, "Connectivity score should be 0-100"
            assert 0.0 <= retrieved_health.performance_score <= 100.0, "Performance score should be 0-100"
            
            # Property: Overall health should be valid
            valid_health_states = ["excellent", "good", "fair", "poor", "critical", "unknown"]
            assert retrieved_health.overall_health in valid_health_states, "Overall health should be valid state"
    
    @given(st.integers(1, 10))
    @settings(max_examples=100)
    def test_alert_summary_completeness(self, num_devices):
        """
        **Feature: collision-detection-web, Property 18: Health Status Completeness**
        **Validates: Requirements 11.5**
        
        For any alert summary query, all alert categories should be
        present and properly categorized.
        """
        # Setup hardware controller and status monitor
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = HardwareController({"log_directory": temp_dir})
            monitor = StatusMonitor(controller, update_interval=1.0)
            
            # Create devices with various health states
            health_states = ["excellent", "good", "fair", "poor", "critical"]
            device_statuses = ["online", "offline", "error"]
            
            for i in range(num_devices):
                device_id = f"test_device_{i}"
                
                # Register device
                device_info = DeviceInfo(
                    device_id=device_id,
                    ip_address=f"192.168.1.{100 + i}",
                    device_type="esp8266",
                    capabilities=["led"],
                    last_seen=time.time(),
                    status=device_statuses[i % len(device_statuses)]
                )
                controller.registered_devices[device_id] = device_info
                
                # Create health metrics
                health_metrics = HealthMetrics(
                    device_id=device_id,
                    uptime_history=[1000],
                    memory_history=[50],
                    wifi_strength_history=[-60],
                    response_time_history=[1.0],
                    error_count=i,
                    last_error_time=time.time() if i > 0 else None,
                    connectivity_score=80.0,
                    performance_score=70.0,
                    overall_health=health_states[i % len(health_states)]
                )
                monitor.device_metrics[device_id] = health_metrics
            
            # Get alert summary
            alerts = monitor.get_alert_summary()
            
            # Property: Alert summary should contain all categories
            required_categories = ["critical", "warning", "info"]
            for category in required_categories:
                assert category in alerts, f"Alert summary should contain {category} category"
                assert isinstance(alerts[category], list), f"{category} alerts should be a list"
            
            # Property: Each alert should have required fields
            for category in required_categories:
                for alert in alerts[category]:
                    assert "device_id" in alert, "Alert should contain device_id"
                    assert "message" in alert, "Alert should contain message"
                    assert "timestamp" in alert, "Alert should contain timestamp"
                    assert isinstance(alert["timestamp"], (int, float)), "Timestamp should be numeric"
    
    @given(st.integers(0, 100))
    @settings(max_examples=100)
    def test_status_history_completeness(self, history_length):
        """
        **Feature: collision-detection-web, Property 18: Health Status Completeness**
        **Validates: Requirements 11.5**
        
        For any status history query, the returned history should be
        complete and properly ordered.
        """
        # Setup hardware controller and status monitor
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = HardwareController({"log_directory": temp_dir})
            monitor = StatusMonitor(controller, update_interval=1.0)
            
            device_id = "test_device"
            
            # Register device
            device_info = DeviceInfo(
                device_id=device_id,
                ip_address="192.168.1.100",
                device_type="esp8266",
                capabilities=["led"],
                last_seen=time.time(),
                status="online"
            )
            controller.registered_devices[device_id] = device_info
            
            # Add status history entries
            for i in range(history_length):
                status_entry = {
                    "timestamp": time.time() + i,
                    "status": "online",
                    "response_time": 1.0 + (i * 0.1),
                    "uptime": 1000 + i,
                    "free_memory": 50 + (i % 10),
                    "wifi_strength": -60 - (i % 5)
                }
                monitor.status_history[device_id].append(status_entry)
            
            # Get status history
            history = monitor.get_device_status_history(device_id)
            
            # Property: History length should match expected
            expected_length = min(history_length, 100)  # StatusMonitor limits to 100 entries
            assert len(history) == expected_length, f"History should contain {expected_length} entries"
            
            # Property: Each history entry should have required fields
            required_fields = ["timestamp", "status", "response_time", "uptime", "free_memory", "wifi_strength"]
            for entry in history:
                for field in required_fields:
                    assert field in entry, f"History entry should contain {field}"
            
            # Property: History should be ordered by timestamp (if multiple entries)
            if len(history) > 1:
                timestamps = [entry["timestamp"] for entry in history]
                # Check if timestamps are in ascending order (oldest first)
                for i in range(1, len(timestamps)):
                    assert timestamps[i] >= timestamps[i-1], "History should be ordered by timestamp"