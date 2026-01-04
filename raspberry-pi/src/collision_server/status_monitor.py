"""
Device Status Monitoring System

Provides comprehensive monitoring of ESP8266 device health, connectivity,
and performance metrics with real-time status reporting to the web interface.
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque

from .hardware_controller import DeviceInfo, DeviceStatus
from .command_logger import DeviceLogEntry, get_command_logger


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HealthMetrics:
    """Health metrics for a device over time"""
    device_id: str
    uptime_history: List[int]
    memory_history: List[int]
    wifi_strength_history: List[int]
    response_time_history: List[float]
    error_count: int
    last_error_time: Optional[float]
    connectivity_score: float
    performance_score: float
    overall_health: str  # excellent, good, fair, poor, critical


@dataclass
class SystemHealth:
    """Overall system health status"""
    total_devices: int
    online_devices: int
    offline_devices: int
    error_devices: int
    average_response_time: float
    system_uptime: float
    cpu_usage: float
    memory_usage: float
    network_status: str
    timestamp: float


class StatusMonitor:
    """
    Comprehensive device status monitoring system.
    
    Monitors ESP8266 device health, connectivity, and performance metrics.
    Provides real-time status reporting and health analytics.
    """
    
    def __init__(self, hardware_controller, update_interval: float = 10.0):
        """
        Initialize the status monitor.
        
        Args:
            hardware_controller: HardwareController instance to monitor
            update_interval: Interval in seconds between status updates
        """
        self.hardware_controller = hardware_controller
        self.update_interval = update_interval
        self.command_logger = get_command_logger()
        
        # Status tracking
        self.device_metrics: Dict[str, HealthMetrics] = {}
        self.status_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.status_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # System monitoring
        self.system_start_time = time.time()
        self.last_system_check = time.time()
        
        # Threading control
        self._running = False
        self._monitor_thread = None
        self._health_thread = None
        
        # Performance thresholds
        self.thresholds = {
            'response_time_warning': 2.0,  # seconds
            'response_time_critical': 5.0,  # seconds
            'memory_warning': 20,  # percentage free
            'memory_critical': 10,  # percentage free
            'wifi_warning': -70,  # dBm
            'wifi_critical': -80,  # dBm
            'offline_timeout': 60.0,  # seconds
        }
        
        logger.info("StatusMonitor initialized")
    
    def start(self):
        """Start the status monitoring services"""
        if self._running:
            logger.warning("StatusMonitor already running")
            return
        
        self._running = True
        
        # Start monitoring threads
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._health_thread = threading.Thread(target=self._health_analysis_loop, daemon=True)
        
        self._monitor_thread.start()
        self._health_thread.start()
        
        logger.info("StatusMonitor started")
    
    def stop(self):
        """Stop the status monitoring services"""
        self._running = False
        
        # Wait for threads to finish
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=2.0)
        
        logger.info("StatusMonitor stopped")
    
    def get_device_health(self, device_id: str) -> Optional[HealthMetrics]:
        """
        Get health metrics for a specific device.
        
        Args:
            device_id: Unique identifier of the device
        
        Returns:
            HealthMetrics object if device exists, None otherwise
        """
        return self.device_metrics.get(device_id)
    
    def get_all_device_health(self) -> Dict[str, HealthMetrics]:
        """Get health metrics for all monitored devices"""
        return self.device_metrics.copy()
    
    def get_system_health(self) -> SystemHealth:
        """
        Get overall system health status.
        
        Returns:
            SystemHealth object with comprehensive system metrics
        """
        registered_devices = self.hardware_controller.get_registered_devices()
        
        # Count device statuses
        total_devices = len(registered_devices)
        online_devices = sum(1 for device in registered_devices.values() if device.status == "online")
        offline_devices = sum(1 for device in registered_devices.values() if device.status == "offline")
        error_devices = sum(1 for device in registered_devices.values() if device.status == "error")
        
        # Calculate average response time
        response_times = []
        for metrics in self.device_metrics.values():
            if metrics.response_time_history:
                response_times.extend(metrics.response_time_history[-10:])  # Last 10 measurements
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        # System uptime
        system_uptime = time.time() - self.system_start_time
        
        # Get system resource usage (simplified for this implementation)
        cpu_usage = self._get_cpu_usage()
        memory_usage = self._get_memory_usage()
        network_status = self._get_network_status()
        
        return SystemHealth(
            total_devices=total_devices,
            online_devices=online_devices,
            offline_devices=offline_devices,
            error_devices=error_devices,
            average_response_time=avg_response_time,
            system_uptime=system_uptime,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            network_status=network_status,
            timestamp=time.time()
        )
    
    def get_device_status_history(self, device_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get status history for a specific device.
        
        Args:
            device_id: Unique identifier of the device
            limit: Maximum number of entries to return
        
        Returns:
            List of status history entries
        """
        history = list(self.status_history[device_id])
        if limit:
            history = history[-limit:]
        return history
    
    def add_status_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback function to be called when status updates occur"""
        self.status_callbacks.append(callback)
    
    def force_status_update(self, device_id: Optional[str] = None):
        """
        Force an immediate status update for a device or all devices.
        
        Args:
            device_id: Optional device ID to update, or None for all devices
        """
        if device_id:
            if device_id in self.hardware_controller.registered_devices:
                self._update_device_status(device_id)
        else:
            for device_id in self.hardware_controller.registered_devices:
                self._update_device_status(device_id)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current alerts and warnings.
        
        Returns:
            Dictionary containing alert summary information
        """
        alerts = {
            "critical": [],
            "warning": [],
            "info": []
        }
        
        for device_id, metrics in self.device_metrics.items():
            device_info = self.hardware_controller.registered_devices.get(device_id)
            if not device_info:
                continue
            
            # Check for critical conditions
            if device_info.status == "offline":
                alerts["critical"].append({
                    "device_id": device_id,
                    "message": f"Device {device_id} is offline",
                    "timestamp": time.time()
                })
            elif metrics.overall_health == "critical":
                alerts["critical"].append({
                    "device_id": device_id,
                    "message": f"Device {device_id} health is critical",
                    "timestamp": time.time()
                })
            
            # Check for warning conditions
            if metrics.overall_health == "poor":
                alerts["warning"].append({
                    "device_id": device_id,
                    "message": f"Device {device_id} health is poor",
                    "timestamp": time.time()
                })
            
            # Check response time warnings
            if metrics.response_time_history:
                avg_response = sum(metrics.response_time_history[-5:]) / len(metrics.response_time_history[-5:])
                if avg_response > self.thresholds['response_time_warning']:
                    alerts["warning"].append({
                        "device_id": device_id,
                        "message": f"Device {device_id} has slow response time: {avg_response:.2f}s",
                        "timestamp": time.time()
                    })
        
        return alerts
    
    def _monitoring_loop(self):
        """Background thread for continuous device status monitoring"""
        while self._running:
            try:
                # Update status for all registered devices
                for device_id in self.hardware_controller.registered_devices:
                    self._update_device_status(device_id)
                
                # Notify status callbacks
                status_update = {
                    "timestamp": time.time(),
                    "device_health": {device_id: asdict(metrics) for device_id, metrics in self.device_metrics.items()},
                    "system_health": asdict(self.get_system_health()),
                    "alerts": self.get_alert_summary()
                }
                
                for callback in self.status_callbacks:
                    try:
                        callback(status_update)
                    except Exception as e:
                        logger.error(f"Status callback error: {e}")
                
                time.sleep(self.update_interval)
            
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(5.0)
    
    def _health_analysis_loop(self):
        """Background thread for health analysis and metric calculation"""
        while self._running:
            try:
                # Analyze health for all devices
                for device_id in self.device_metrics:
                    self._analyze_device_health(device_id)
                
                time.sleep(30.0)  # Run health analysis every 30 seconds
            
            except Exception as e:
                logger.error(f"Health analysis loop error: {e}")
                time.sleep(10.0)
    
    def _update_device_status(self, device_id: str):
        """Update status for a specific device"""
        device_info = self.hardware_controller.registered_devices.get(device_id)
        if not device_info:
            return
        
        start_time = time.time()
        
        # Query device status
        status = self.hardware_controller.get_device_status(device_id)
        response_time = time.time() - start_time
        
        # Initialize metrics if not exists
        if device_id not in self.device_metrics:
            self.device_metrics[device_id] = HealthMetrics(
                device_id=device_id,
                uptime_history=[],
                memory_history=[],
                wifi_strength_history=[],
                response_time_history=[],
                error_count=0,
                last_error_time=None,
                connectivity_score=0.0,
                performance_score=0.0,
                overall_health="unknown"
            )
        
        metrics = self.device_metrics[device_id]
        
        # Update metrics
        metrics.response_time_history.append(response_time)
        if len(metrics.response_time_history) > 50:
            metrics.response_time_history = metrics.response_time_history[-25:]
        
        if status:
            # Device responded successfully
            metrics.uptime_history.append(status.uptime)
            metrics.memory_history.append(status.free_memory)
            metrics.wifi_strength_history.append(status.wifi_strength)
            
            # Trim history lists
            for history_list in [metrics.uptime_history, metrics.memory_history, metrics.wifi_strength_history]:
                if len(history_list) > 50:
                    history_list[:] = history_list[-25:]
            
            # Log successful status update
            device_log_entry = DeviceLogEntry(
                device_id=device_id,
                event_type="status_update",
                timestamp=time.time(),
                data={
                    "status": status.status,
                    "uptime": status.uptime,
                    "free_memory": status.free_memory,
                    "wifi_strength": status.wifi_strength,
                    "response_time": response_time
                },
                severity="info"
            )
            self.command_logger.log_device_event(device_log_entry)
        
        else:
            # Device failed to respond
            metrics.error_count += 1
            metrics.last_error_time = time.time()
            
            # Log error
            device_log_entry = DeviceLogEntry(
                device_id=device_id,
                event_type="error",
                timestamp=time.time(),
                data={
                    "error_type": "status_query_failed",
                    "response_time": response_time
                },
                severity="error"
            )
            self.command_logger.log_device_event(device_log_entry)
        
        # Add to status history
        status_entry = {
            "timestamp": time.time(),
            "status": status.status if status else "error",
            "response_time": response_time,
            "uptime": status.uptime if status else 0,
            "free_memory": status.free_memory if status else 0,
            "wifi_strength": status.wifi_strength if status else -100
        }
        self.status_history[device_id].append(status_entry)
    
    def _analyze_device_health(self, device_id: str):
        """Analyze and update health metrics for a device"""
        metrics = self.device_metrics.get(device_id)
        if not metrics:
            return
        
        device_info = self.hardware_controller.registered_devices.get(device_id)
        if not device_info:
            return
        
        # Calculate connectivity score (0-100)
        connectivity_factors = []
        
        # Response time factor
        if metrics.response_time_history:
            avg_response = sum(metrics.response_time_history[-10:]) / len(metrics.response_time_history[-10:])
            if avg_response < 1.0:
                connectivity_factors.append(100)
            elif avg_response < 2.0:
                connectivity_factors.append(80)
            elif avg_response < 5.0:
                connectivity_factors.append(60)
            else:
                connectivity_factors.append(20)
        
        # WiFi strength factor
        if metrics.wifi_strength_history:
            avg_wifi = sum(metrics.wifi_strength_history[-10:]) / len(metrics.wifi_strength_history[-10:])
            if avg_wifi > -50:
                connectivity_factors.append(100)
            elif avg_wifi > -60:
                connectivity_factors.append(80)
            elif avg_wifi > -70:
                connectivity_factors.append(60)
            elif avg_wifi > -80:
                connectivity_factors.append(40)
            else:
                connectivity_factors.append(20)
        
        # Error rate factor
        total_checks = len(metrics.response_time_history)
        if total_checks > 0:
            error_rate = metrics.error_count / total_checks
            if error_rate < 0.01:
                connectivity_factors.append(100)
            elif error_rate < 0.05:
                connectivity_factors.append(80)
            elif error_rate < 0.1:
                connectivity_factors.append(60)
            else:
                connectivity_factors.append(20)
        
        metrics.connectivity_score = sum(connectivity_factors) / len(connectivity_factors) if connectivity_factors else 0
        
        # Calculate performance score (0-100)
        performance_factors = []
        
        # Memory usage factor
        if metrics.memory_history:
            avg_memory = sum(metrics.memory_history[-10:]) / len(metrics.memory_history[-10:])
            if avg_memory > 50:
                performance_factors.append(100)
            elif avg_memory > 30:
                performance_factors.append(80)
            elif avg_memory > 20:
                performance_factors.append(60)
            elif avg_memory > 10:
                performance_factors.append(40)
            else:
                performance_factors.append(20)
        
        # Uptime stability factor
        if len(metrics.uptime_history) > 1:
            uptime_changes = sum(1 for i in range(1, len(metrics.uptime_history)) 
                               if metrics.uptime_history[i] < metrics.uptime_history[i-1])
            stability = max(0, 100 - (uptime_changes * 10))
            performance_factors.append(stability)
        
        metrics.performance_score = sum(performance_factors) / len(performance_factors) if performance_factors else 0
        
        # Determine overall health
        overall_score = (metrics.connectivity_score + metrics.performance_score) / 2
        
        if device_info.status == "offline":
            metrics.overall_health = "critical"
        elif overall_score >= 90:
            metrics.overall_health = "excellent"
        elif overall_score >= 75:
            metrics.overall_health = "good"
        elif overall_score >= 60:
            metrics.overall_health = "fair"
        elif overall_score >= 40:
            metrics.overall_health = "poor"
        else:
            metrics.overall_health = "critical"
    
    def _get_cpu_usage(self) -> float:
        """Get system CPU usage percentage (simplified implementation)"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            # Fallback if psutil not available
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get system memory usage percentage (simplified implementation)"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            # Fallback if psutil not available
            return 0.0
    
    def _get_network_status(self) -> str:
        """Get network connectivity status (simplified implementation)"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return "connected"
        except OSError:
            return "disconnected"