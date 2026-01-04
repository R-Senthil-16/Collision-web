"""
Property-based tests for hardware communication system.

Tests universal properties for ESP8266 device communication, command dispatch,
and logging completeness using Hypothesis for comprehensive input coverage.

**Feature: collision-detection-web, Property 14: Hardware Command Dispatch**
**Feature: collision-detection-web, Property 15: Command Logging Completeness**
**Validates: Requirements 10.1, 10.4**
"""

import json
import time
import uuid
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, HealthCheck
import pytest

from collision_server.hardware_controller import (
    HardwareController, 
    HardwareCommand, 
    DeviceInfo,
    DeviceStatus
)
from collision_server.command_logger import CommandLogger, CommandLogEntry, DeviceLogEntry


# Simplified test data generators for better performance
def simple_device_info(device_id: str = "test_device") -> DeviceInfo:
    """Generate a simple DeviceInfo object for testing"""
    return DeviceInfo(
        device_id=device_id,
        ip_address="192.168.1.100",
        device_type="esp8266",
        capabilities=["led", "servo"],
        last_seen=time.time(),
        status="online"
    )


def simple_hardware_command(device_id: str = "test_device", action: str = "led_on") -> HardwareCommand:
    """Generate a simple HardwareCommand object for testing"""
    return HardwareCommand(
        device_id=device_id,
        action=action,
        parameters={"color": "red", "brightness": 255},
        timestamp=time.time(),
        priority=1
    )


# Optimized strategies for better performance
device_id_strategy = st.text(min_size=3, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz0123456789")
action_strategy = st.sampled_from(["led_on", "led_off", "servo_move", "alert"])
simple_parameters_strategy = st.fixed_dictionaries({
    "color": st.sampled_from(["red", "green", "blue"]),
    "brightness": st.integers(0, 255)
})


@st.composite
def simple_device_strategy(draw):
    """Generate simple DeviceInfo objects with minimal complexity"""
    device_id = draw(device_id_strategy)
    return DeviceInfo(
        device_id=device_id,
        ip_address="192.168.1.100",
        device_type="esp8266",
        capabilities=["led"],
        last_seen=time.time(),
        status="online"
    )


@st.composite
def simple_command_strategy(draw):
    """Generate simple HardwareCommand objects with minimal complexity"""
    device_id = draw(device_id_strategy)
    action = draw(action_strategy)
    parameters = draw(simple_parameters_strategy)
    
    return HardwareCommand(
        device_id=device_id,
        action=action,
        parameters=parameters,
        timestamp=time.time(),
        priority=1
    )


class TestHardwareCommandDispatch:
    """
    Property-based tests for hardware command dispatch functionality.
    
    **Property 14: Hardware Command Dispatch**
    *For any* detected collision event, the Hardware_Controller should send 
    the appropriate commands to all configured ESP8266 devices without delay or omission.
    """
    
    def setup_method(self):
        """Setup fresh test environment for each test method"""
        # Create temporary directory for isolated logging
        self.temp_dir = tempfile.mkdtemp()
        
        # Reset global logger state by creating fresh instance
        import collision_server.command_logger as logger_module
        logger_module._command_logger = None
    
    def teardown_method(self):
        """Cleanup after each test method"""
        # Clean up temporary directory
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Reset global logger state
        import collision_server.command_logger as logger_module
        logger_module._command_logger = None
    
    @given(simple_device_strategy(), simple_command_strategy())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])  # Suppress slow generation check
    def test_command_dispatch_completeness(self, device_info, command):
        """
        **Feature: collision-detection-web, Property 14: Hardware Command Dispatch**
        **Validates: Requirements 10.1**
        
        For any registered device and valid command, the hardware controller
        should successfully queue and attempt to dispatch the command.
        """
        # Setup hardware controller with isolated logging
        controller = HardwareController({"log_directory": self.temp_dir})
        
        # Register the device
        controller.registered_devices[device_info.device_id] = device_info
        
        # Mock the command execution to avoid network calls
        with patch.object(controller, '_execute_command', return_value=True) as mock_execute:
            # Send command to the registered device
            command.device_id = device_info.device_id
            success = controller.send_command(
                device_id=command.device_id,
                command=command.action,
                parameters=command.parameters
            )
            
            # Property: Command should be successfully queued
            assert success is True, f"Command {command.action} should be queued successfully for device {device_info.device_id}"
            
            # Property: Command should appear in queue
            assert not controller.command_queue.empty(), "Command queue should contain the dispatched command"
    
    @given(st.lists(simple_device_strategy(), min_size=1, max_size=3), st.text(min_size=1, max_size=20))
    @settings(max_examples=30)  # Reduced for better performance
    def test_broadcast_alert_completeness(self, device_list, alert_message):
        """
        **Feature: collision-detection-web, Property 14: Hardware Command Dispatch**
        **Validates: Requirements 10.1**
        
        For any list of registered devices and alert message, broadcast_alert
        should send commands to all devices without omission.
        """
        # Setup hardware controller with isolated logging
        controller = HardwareController({"log_directory": self.temp_dir})
        
        # Register all devices with unique IDs
        unique_devices = {}
        for i, device in enumerate(device_list):
            unique_id = f"{device.device_id}_{i}"
            device.device_id = unique_id
            unique_devices[unique_id] = device
            controller.registered_devices[unique_id] = device
        
        # Mock command execution
        with patch.object(controller, 'send_command', return_value=True) as mock_send:
            # Broadcast alert to all devices
            successful_count = controller.broadcast_alert(alert_message, "collision")
            
            # Property: All registered devices should receive the alert
            assert successful_count == len(unique_devices), f"Alert should be sent to all {len(unique_devices)} devices"
            
            # Property: send_command should be called once per device
            assert mock_send.call_count == len(unique_devices), "send_command should be called for each registered device"
            
            # Property: All calls should be for alert commands
            for call in mock_send.call_args_list:
                args, kwargs = call
                assert args[1] == "alert", "All broadcast calls should be for 'alert' command"
                assert "message" in args[2], "Alert parameters should contain message"
                assert args[2]["message"] == alert_message, "Alert message should match input"
    
    @given(simple_device_strategy())
    @settings(max_examples=30)  # Reduced for better performance
    def test_unregistered_device_command_rejection(self, device_info):
        """
        **Feature: collision-detection-web, Property 14: Hardware Command Dispatch**
        **Validates: Requirements 10.1**
        
        For any unregistered device, command dispatch should fail gracefully
        without affecting system state.
        """
        # Setup hardware controller with isolated logging
        controller = HardwareController({"log_directory": self.temp_dir})
        
        # Attempt to send command to unregistered device
        success = controller.send_command(
            device_id=device_info.device_id,
            command="led_on",
            parameters={"color": "red"}
        )
        
        # Property: Command to unregistered device should fail
        assert success is False, f"Command to unregistered device {device_info.device_id} should fail"
        
        # Property: Command queue should remain empty
        assert controller.command_queue.empty(), "Command queue should remain empty for unregistered device commands"


class TestCommandLoggingCompleteness:
    """
    Property-based tests for command logging completeness.
    
    **Property 15: Command Logging Completeness**
    *For any* hardware command sent to ESP8266 devices, the system should log 
    the command with accurate timestamp, device ID, and command parameters.
    """
    
    def setup_method(self):
        """Setup fresh test environment for each test method"""
        # Create temporary directory for isolated logging
        self.temp_dir = tempfile.mkdtemp()
        
        # Reset global logger state by creating fresh instance
        import collision_server.command_logger as logger_module
        logger_module._command_logger = None
    
    def teardown_method(self):
        """Cleanup after each test method"""
        # Clean up temporary directory
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Reset global logger state
        import collision_server.command_logger as logger_module
        logger_module._command_logger = None
    
    @given(simple_device_strategy(), simple_command_strategy())
    @settings(max_examples=30)  # Reduced for better performance
    def test_command_logging_accuracy(self, device_info, command):
        """
        **Feature: collision-detection-web, Property 15: Command Logging Completeness**
        **Validates: Requirements 10.4**
        
        For any command sent to a registered device, all command details
        should be accurately logged with complete information.
        """
        # Setup hardware controller with isolated logging
        controller = HardwareController({"log_directory": self.temp_dir})
        
        # Register the device
        controller.registered_devices[device_info.device_id] = device_info
        
        # Send command
        command.device_id = device_info.device_id
        success = controller.send_command(
            device_id=command.device_id,
            command=command.action,
            parameters=command.parameters
        )
        
        # Property: Command should be logged
        assert success is True, "Command should be sent successfully"
        
        # Get command log
        command_history = controller.get_detailed_command_log(device_id=device_info.device_id)
        
        # Property: Log should contain the command
        assert len(command_history) >= 1, "Command log should contain at least one entry"
        
        # Property: Most recent log entry should match sent command
        latest_log = command_history[0]  # Most recent first
        assert latest_log["device_id"] == command.device_id, "Logged device_id should match command"
        assert latest_log["action"] == command.action, "Logged action should match command"
        assert latest_log["parameters"] == command.parameters, "Logged parameters should match command"
        assert "timestamp" in latest_log, "Log entry should contain timestamp"
        assert "command_id" in latest_log, "Log entry should contain unique command_id"
    
    def test_multiple_command_logging_completeness(self):
        """
        **Feature: collision-detection-web, Property 15: Command Logging Completeness**
        **Validates: Requirements 10.4**
        
        For any sequence of commands, all commands should be logged in order
        with no missing entries or data corruption.
        """
        # Setup hardware controller with isolated logging
        controller = HardwareController({"log_directory": self.temp_dir})
        
        # Create and register a test device
        test_device = simple_device_info("isolated_test_device")
        controller.registered_devices["isolated_test_device"] = test_device
        
        # Send multiple commands
        num_commands = 3
        sent_commands = []
        for i in range(num_commands):
            command = simple_hardware_command("isolated_test_device", f"led_on_{i}")
            success = controller.send_command(
                device_id=command.device_id,
                command=command.action,
                parameters=command.parameters
            )
            if success:
                sent_commands.append(command)
        
        # Get command log
        command_history = controller.get_detailed_command_log(device_id="isolated_test_device")
        
        # Property: All sent commands should be logged
        assert len(command_history) == len(sent_commands), f"Should log all {len(sent_commands)} commands, but found {len(command_history)}"
        
        # Property: Commands should be logged in reverse chronological order (most recent first)
        for i in range(len(command_history) - 1):
            current_timestamp = command_history[i]["timestamp"]
            next_timestamp = command_history[i + 1]["timestamp"]
            assert current_timestamp >= next_timestamp, "Commands should be ordered by timestamp (newest first)"
        
        # Property: Each logged command should have all required fields
        required_fields = ["command_id", "device_id", "action", "parameters", "timestamp", "status"]
        for log_entry in command_history:
            for field in required_fields:
                assert field in log_entry, f"Log entry should contain required field: {field}"
        
        # Property: Command ID should be unique
        command_ids = [entry["command_id"] for entry in command_history]
        assert len(command_ids) == len(set(command_ids)), "All command IDs should be unique"
    
    @given(simple_device_strategy())
    @settings(max_examples=20)  # Reduced for better performance
    def test_device_event_logging_completeness(self, device_info):
        """
        **Feature: collision-detection-web, Property 15: Command Logging Completeness**
        **Validates: Requirements 10.4**
        
        For any device registration or status change, the event should be
        logged with complete information and accurate timestamps.
        """
        # Setup hardware controller with isolated logging
        controller = HardwareController({"log_directory": self.temp_dir})
        
        # Register the device (should trigger logging)
        controller._register_device(device_info)
        
        # Get device event log
        device_events = controller.get_device_event_log(device_id=device_info.device_id)
        
        # Property: Device registration should be logged
        assert len(device_events) >= 1, "Device registration should create log entry"
        
        # Property: Registration event should contain complete information
        registration_event = device_events[0]  # Most recent first
        assert registration_event["device_id"] == device_info.device_id, "Event should log correct device_id"
        assert registration_event["event_type"] == "connection", "Registration should be logged as connection event"
        assert "timestamp" in registration_event, "Event should contain timestamp"
        assert "data" in registration_event, "Event should contain data field"
        
        # Property: Event data should contain device information
        event_data = registration_event["data"]
        assert "ip_address" in event_data, "Event data should contain ip_address"
        assert "device_type" in event_data, "Event data should contain device_type"
        assert "capabilities" in event_data, "Event data should contain capabilities"
        assert event_data["ip_address"] == device_info.ip_address, "Event should log correct IP address"
    
    def test_command_statistics_accuracy(self):
        """
        **Feature: collision-detection-web, Property 15: Command Logging Completeness**
        **Validates: Requirements 10.4**
        
        For any number of executed commands, statistics should accurately
        reflect the actual command execution history.
        """
        # Setup hardware controller with isolated logging
        controller = HardwareController({"log_directory": self.temp_dir})
        
        # Create and register a test device
        test_device = simple_device_info("stats_isolated_device")
        controller.registered_devices["stats_isolated_device"] = test_device
        
        # Send specific number of commands
        num_commands = 2
        for i in range(num_commands):
            controller.send_command(
                device_id="stats_isolated_device",
                command="led_on",
                parameters={"color": "red", "brightness": i + 100}
            )
        
        # Get command statistics
        stats = controller.get_command_statistics(device_id="stats_isolated_device")
        
        # Property: Statistics should reflect actual command count
        assert stats["total_commands"] == num_commands, f"Statistics should show {num_commands} total commands, but found {stats['total_commands']}"
        
        # Property: Statistics should contain required fields
        required_stats = ["total_commands", "status_counts", "success_rate"]
        for stat_field in required_stats:
            assert stat_field in stats, f"Statistics should contain {stat_field}"
        
        # Property: Status counts should sum to total commands
        status_sum = sum(stats["status_counts"].values())
        assert status_sum == num_commands, f"Sum of status counts should equal total commands: expected {num_commands}, got {status_sum}"