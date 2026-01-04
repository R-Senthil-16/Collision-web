"""
Hardware Controller for ESP8266 Communication

Manages WiFi communication with ESP8266 devices for collision response actions.
Implements device discovery, registration, and command dispatch functionality.
"""

import asyncio
import json
import logging
import socket
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from queue import Queue, Empty
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from .command_logger import CommandLogger, CommandLogEntry, DeviceLogEntry, get_command_logger


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HardwareCommand:
    """Represents a command to be sent to an ESP8266 device"""
    device_id: str
    action: str
    parameters: Dict[str, Any]
    timestamp: float
    priority: int = 1  # 1 = high, 2 = medium, 3 = low


@dataclass
class DeviceInfo:
    """Information about a registered ESP8266 device"""
    device_id: str
    ip_address: str
    device_type: str
    capabilities: List[str]
    last_seen: float
    status: str = "online"  # online, offline, error


@dataclass
class DeviceStatus:
    """Status information from an ESP8266 device"""
    device_id: str
    status: str
    uptime: int
    free_memory: int
    wifi_strength: int
    sensor_data: Dict[str, Any]
    timestamp: float


class HardwareController:
    """
    Controls communication with ESP8266 devices for collision response actions.
    
    Handles device discovery, registration, command dispatch, and status monitoring.
    Implements WiFi communication protocols for reliable device interaction.
    """
    
    def __init__(self, device_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the hardware controller.
        
        Args:
            device_config: Configuration dictionary for device settings
        """
        self.device_config = device_config or {}
        self.registered_devices: Dict[str, DeviceInfo] = {}
        self.command_queue = Queue()
        self.command_log: List[HardwareCommand] = []
        self.status_callbacks: List[Callable[[DeviceStatus], None]] = []
        
        # Initialize command logger
        log_directory = self.device_config.get('log_directory', '/tmp/collision_logs')
        self.command_logger = get_command_logger(log_directory)
        
        # Communication settings
        self.discovery_port = self.device_config.get('discovery_port', 8888)
        self.command_port = self.device_config.get('command_port', 8889)
        self.status_port = self.device_config.get('status_port', 8890)
        self.network_timeout = self.device_config.get('network_timeout', 5.0)
        self.discovery_interval = self.device_config.get('discovery_interval', 30.0)
        
        # Threading control
        self._running = False
        self._discovery_thread = None
        self._command_thread = None
        self._status_thread = None
        
        logger.info("HardwareController initialized")
    
    def start(self):
        """Start the hardware controller services"""
        if self._running:
            logger.warning("HardwareController already running")
            return
        
        self._running = True
        
        # Start background threads
        self._discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self._command_thread = threading.Thread(target=self._command_loop, daemon=True)
        self._status_thread = threading.Thread(target=self._status_loop, daemon=True)
        
        self._discovery_thread.start()
        self._command_thread.start()
        self._status_thread.start()
        
        logger.info("HardwareController started")
    
    def stop(self):
        """Stop the hardware controller services"""
        self._running = False
        
        # Wait for threads to finish
        if self._discovery_thread and self._discovery_thread.is_alive():
            self._discovery_thread.join(timeout=2.0)
        if self._command_thread and self._command_thread.is_alive():
            self._command_thread.join(timeout=2.0)
        if self._status_thread and self._status_thread.is_alive():
            self._status_thread.join(timeout=2.0)
        
        logger.info("HardwareController stopped")
    
    def connect_devices(self) -> bool:
        """
        Initiate device discovery and connection process.
        
        Returns:
            bool: True if at least one device was discovered, False otherwise
        """
        logger.info("Starting device discovery...")
        discovered_devices = self._discover_devices()
        
        for device_info in discovered_devices:
            self._register_device(device_info)
        
        logger.info(f"Connected to {len(self.registered_devices)} devices")
        return len(self.registered_devices) > 0
    
    def send_command(self, device_id: str, command: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send a command to a specific ESP8266 device.
        
        Args:
            device_id: Unique identifier of the target device
            command: Command string to execute
            parameters: Optional parameters for the command
        
        Returns:
            bool: True if command was queued successfully, False otherwise
        """
        if device_id not in self.registered_devices:
            logger.error(f"Device {device_id} not registered")
            return False
        
        # Generate unique command ID for tracking
        command_id = str(uuid.uuid4())
        
        hw_command = HardwareCommand(
            device_id=device_id,
            action=command,
            parameters=parameters or {},
            timestamp=time.time(),
            priority=1
        )
        
        # Create log entry for command tracking
        log_entry = CommandLogEntry(
            command_id=command_id,
            device_id=device_id,
            action=command,
            parameters=parameters or {},
            timestamp=time.time(),
            status="pending"
        )
        
        try:
            # Add command ID to hardware command for tracking
            hw_command.parameters['_command_id'] = command_id
            
            self.command_queue.put(hw_command, timeout=1.0)
            
            # Log the command
            self.command_logger.log_command(log_entry)
            
            logger.info(f"Command queued for device {device_id}: {command} (ID: {command_id})")
            return True
        except Exception as e:
            # Update log entry with failure
            log_entry.status = "failed"
            log_entry.error_message = str(e)
            self.command_logger.log_command(log_entry)
            
            logger.error(f"Failed to queue command for device {device_id}: {e}")
            return False
    
    def get_device_status(self, device_id: str) -> Optional[DeviceStatus]:
        """
        Get the current status of a specific device.
        
        Args:
            device_id: Unique identifier of the device
        
        Returns:
            DeviceStatus object if device exists and is reachable, None otherwise
        """
        if device_id not in self.registered_devices:
            logger.error(f"Device {device_id} not registered")
            return None
        
        device_info = self.registered_devices[device_id]
        return self._query_device_status(device_info)
    
    def broadcast_alert(self, message: str, alert_type: str = "collision") -> int:
        """
        Broadcast an alert message to all connected devices.
        
        Args:
            message: Alert message to broadcast
            alert_type: Type of alert (collision, warning, info)
        
        Returns:
            int: Number of devices that received the alert
        """
        successful_broadcasts = 0
        
        for device_id in self.registered_devices:
            parameters = {
                "message": message,
                "alert_type": alert_type,
                "timestamp": time.time()
            }
            
            if self.send_command(device_id, "alert", parameters):
                successful_broadcasts += 1
        
        logger.info(f"Broadcast alert to {successful_broadcasts} devices: {message}")
        return successful_broadcasts
    
    def get_registered_devices(self) -> Dict[str, DeviceInfo]:
        """Get a copy of all registered devices"""
        return self.registered_devices.copy()
    
    def get_command_log(self, limit: Optional[int] = None) -> List[HardwareCommand]:
        """
        Get the command log history.
        
        Args:
            limit: Maximum number of commands to return (most recent first)
        
        Returns:
            List of HardwareCommand objects
        """
        if limit:
            return self.command_log[-limit:]
        return self.command_log.copy()
    
    def add_status_callback(self, callback: Callable[[DeviceStatus], None]):
        """Add a callback function to be called when device status updates are received"""
        self.status_callbacks.append(callback)
    
    def get_command_statistics(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get command execution statistics from the logger.
        
        Args:
            device_id: Optional device ID to filter statistics
        
        Returns:
            Dictionary containing command execution statistics
        """
        return self.command_logger.get_command_statistics(device_id)
    
    def get_detailed_command_log(self, device_id: Optional[str] = None, 
                               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get detailed command log with execution status and timing.
        
        Args:
            device_id: Optional device ID to filter logs
            limit: Maximum number of entries to return
        
        Returns:
            List of command log entries as dictionaries
        """
        entries = self.command_logger.get_command_history(device_id, limit)
        return [asdict(entry) for entry in entries]
    
    def get_device_event_log(self, device_id: Optional[str] = None,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get device event log (connections, disconnections, errors).
        
        Args:
            device_id: Optional device ID to filter logs
            limit: Maximum number of entries to return
        
        Returns:
            List of device event log entries as dictionaries
        """
        entries = self.command_logger.get_device_events(device_id, limit=limit)
        return [asdict(entry) for entry in entries]
    
    def _discover_devices(self) -> List[DeviceInfo]:
        """
        Discover ESP8266 devices on the network using UDP broadcast.
        
        Returns:
            List of discovered DeviceInfo objects
        """
        discovered = []
        
        try:
            # Create UDP socket for discovery
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(self.network_timeout)
            
            # Send discovery broadcast
            discovery_message = json.dumps({
                "type": "discovery",
                "timestamp": time.time()
            })
            
            sock.sendto(discovery_message.encode(), ('<broadcast>', self.discovery_port))
            
            # Listen for responses
            start_time = time.time()
            while time.time() - start_time < self.network_timeout:
                try:
                    data, addr = sock.recvfrom(1024)
                    response = json.loads(data.decode())
                    
                    if response.get("type") == "discovery_response":
                        device_info = DeviceInfo(
                            device_id=response.get("device_id"),
                            ip_address=addr[0],
                            device_type=response.get("device_type", "esp8266"),
                            capabilities=response.get("capabilities", []),
                            last_seen=time.time(),
                            status="online"
                        )
                        discovered.append(device_info)
                        logger.info(f"Discovered device: {device_info.device_id} at {device_info.ip_address}")
                
                except socket.timeout:
                    continue
                except json.JSONDecodeError:
                    logger.warning(f"Invalid discovery response from {addr[0]}")
                    continue
            
            sock.close()
        
        except Exception as e:
            logger.error(f"Device discovery failed: {e}")
        
        return discovered
    
    def _register_device(self, device_info: DeviceInfo):
        """Register a discovered device"""
        self.registered_devices[device_info.device_id] = device_info
        
        # Log device registration
        device_log_entry = DeviceLogEntry(
            device_id=device_info.device_id,
            event_type="connection",
            timestamp=time.time(),
            data={
                "ip_address": device_info.ip_address,
                "device_type": device_info.device_type,
                "capabilities": device_info.capabilities
            },
            severity="info"
        )
        self.command_logger.log_device_event(device_log_entry)
        
        logger.info(f"Registered device: {device_info.device_id}")
    
    def _discovery_loop(self):
        """Background thread for periodic device discovery"""
        while self._running:
            try:
                # Periodic device discovery
                discovered_devices = self._discover_devices()
                
                # Update existing devices and add new ones
                for device_info in discovered_devices:
                    if device_info.device_id in self.registered_devices:
                        # Update last_seen timestamp
                        self.registered_devices[device_info.device_id].last_seen = device_info.last_seen
                        self.registered_devices[device_info.device_id].status = "online"
                    else:
                        # Register new device
                        self._register_device(device_info)
                
                # Mark devices as offline if not seen recently
                current_time = time.time()
                for device_id, device_info in self.registered_devices.items():
                    if current_time - device_info.last_seen > self.discovery_interval * 2:
                        if device_info.status != "offline":
                            device_info.status = "offline"
                            
                            # Log device disconnection
                            device_log_entry = DeviceLogEntry(
                                device_id=device_id,
                                event_type="disconnection",
                                timestamp=current_time,
                                data={"reason": "discovery_timeout"},
                                severity="warning"
                            )
                            self.command_logger.log_device_event(device_log_entry)
                
                time.sleep(self.discovery_interval)
            
            except Exception as e:
                logger.error(f"Discovery loop error: {e}")
                time.sleep(5.0)
    
    def _command_loop(self):
        """Background thread for processing command queue"""
        while self._running:
            try:
                # Get command from queue with timeout
                command = self.command_queue.get(timeout=1.0)
                
                # Extract command ID for tracking
                command_id = command.parameters.get('_command_id')
                start_time = time.time()
                
                # Execute command
                success = self._execute_command(command)
                execution_time = time.time() - start_time
                
                # Update command status in logger
                if command_id:
                    status = "success" if success else "failed"
                    self.command_logger.update_command_status(
                        command_id=command_id,
                        status=status,
                        execution_time=execution_time
                    )
                
                # Log command execution (legacy)
                self.command_log.append(command)
                
                # Keep log size manageable
                if len(self.command_log) > 1000:
                    self.command_log = self.command_log[-500:]
                
                if success:
                    logger.info(f"Command executed successfully: {command.action} on {command.device_id}")
                else:
                    logger.error(f"Command execution failed: {command.action} on {command.device_id}")
            
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Command loop error: {e}")
    
    def _status_loop(self):
        """Background thread for monitoring device status"""
        while self._running:
            try:
                for device_id, device_info in self.registered_devices.items():
                    if device_info.status == "online":
                        status = self._query_device_status(device_info)
                        if status:
                            # Notify status callbacks
                            for callback in self.status_callbacks:
                                try:
                                    callback(status)
                                except Exception as e:
                                    logger.error(f"Status callback error: {e}")
                
                time.sleep(10.0)  # Check status every 10 seconds
            
            except Exception as e:
                logger.error(f"Status loop error: {e}")
                time.sleep(5.0)
    
    def _execute_command(self, command: HardwareCommand) -> bool:
        """
        Execute a hardware command on the target device.
        
        Args:
            command: HardwareCommand to execute
        
        Returns:
            bool: True if command was executed successfully, False otherwise
        """
        device_info = self.registered_devices.get(command.device_id)
        if not device_info:
            logger.error(f"Device {command.device_id} not found")
            return False
        
        try:
            # Prepare command payload
            payload = {
                "command": command.action,
                "parameters": command.parameters,
                "timestamp": command.timestamp
            }
            
            # Send HTTP POST request to device
            url = f"http://{device_info.ip_address}:{self.command_port}/command"
            response = requests.post(
                url,
                json=payload,
                timeout=self.network_timeout
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Device {command.device_id} returned status {response.status_code}")
                return False
        
        except (RequestException, Timeout, ConnectionError) as e:
            logger.error(f"Failed to send command to device {command.device_id}: {e}")
            # Mark device as offline if communication fails
            device_info.status = "offline"
            return False
    
    def _query_device_status(self, device_info: DeviceInfo) -> Optional[DeviceStatus]:
        """
        Query status information from a device.
        
        Args:
            device_info: DeviceInfo object for the target device
        
        Returns:
            DeviceStatus object if successful, None otherwise
        """
        try:
            url = f"http://{device_info.ip_address}:{self.status_port}/status"
            response = requests.get(url, timeout=self.network_timeout)
            
            if response.status_code == 200:
                data = response.json()
                return DeviceStatus(
                    device_id=device_info.device_id,
                    status=data.get("status", "unknown"),
                    uptime=data.get("uptime", 0),
                    free_memory=data.get("free_memory", 0),
                    wifi_strength=data.get("wifi_strength", 0),
                    sensor_data=data.get("sensor_data", {}),
                    timestamp=time.time()
                )
            else:
                logger.warning(f"Device {device_info.device_id} status query returned {response.status_code}")
                return None
        
        except (RequestException, Timeout, ConnectionError) as e:
            logger.warning(f"Failed to query status from device {device_info.device_id}: {e}")
            return None