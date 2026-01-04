"""
Command Logger for Hardware Controller

Provides comprehensive logging and tracking of hardware commands with timestamps,
execution status, and detailed audit trails for collision response actions.
"""

import json
import logging
import os
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CommandLogEntry:
    """Represents a logged command execution with full details"""
    command_id: str
    device_id: str
    action: str
    parameters: Dict[str, Any]
    timestamp: float
    execution_time: Optional[float] = None
    status: str = "pending"  # pending, success, failed, timeout
    error_message: Optional[str] = None
    retry_count: int = 0
    response_data: Optional[Dict[str, Any]] = None


@dataclass
class DeviceLogEntry:
    """Represents a device status or event log entry"""
    device_id: str
    event_type: str  # status_update, connection, disconnection, error
    timestamp: float
    data: Dict[str, Any]
    severity: str = "info"  # debug, info, warning, error, critical


class CommandLogger:
    """
    Comprehensive logging system for hardware commands and device events.
    
    Provides persistent logging, audit trails, and query capabilities for
    command execution tracking and system monitoring.
    """
    
    def __init__(self, log_directory: str = "/tmp/collision_logs"):
        """
        Initialize the command logger.
        
        Args:
            log_directory: Directory path for storing log files
        """
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # In-memory log storage for quick access
        self.command_log: List[CommandLogEntry] = []
        self.device_log: List[DeviceLogEntry] = []
        
        # File paths
        self.command_log_file = self.log_directory / "command_log.jsonl"
        self.device_log_file = self.log_directory / "device_log.jsonl"
        self.daily_log_file = self.log_directory / f"daily_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Threading lock for thread-safe operations
        self._lock = threading.Lock()
        
        # Load existing logs
        self._load_existing_logs()
        
        logger.info(f"CommandLogger initialized with log directory: {log_directory}")
    
    def log_command(self, command_entry: CommandLogEntry):
        """
        Log a command execution entry.
        
        Args:
            command_entry: CommandLogEntry object to log
        """
        with self._lock:
            # Add to in-memory log
            self.command_log.append(command_entry)
            
            # Write to persistent storage
            self._write_command_to_file(command_entry)
            
            # Keep in-memory log size manageable
            if len(self.command_log) > 1000:
                self.command_log = self.command_log[-500:]
        
        logger.info(f"Command logged: {command_entry.action} on {command_entry.device_id} - {command_entry.status}")
    
    def log_device_event(self, device_entry: DeviceLogEntry):
        """
        Log a device event entry.
        
        Args:
            device_entry: DeviceLogEntry object to log
        """
        with self._lock:
            # Add to in-memory log
            self.device_log.append(device_entry)
            
            # Write to persistent storage
            self._write_device_event_to_file(device_entry)
            
            # Keep in-memory log size manageable
            if len(self.device_log) > 1000:
                self.device_log = self.device_log[-500:]
        
        logger.info(f"Device event logged: {device_entry.event_type} for {device_entry.device_id}")
    
    def update_command_status(self, command_id: str, status: str, 
                            execution_time: Optional[float] = None,
                            error_message: Optional[str] = None,
                            response_data: Optional[Dict[str, Any]] = None):
        """
        Update the status of a previously logged command.
        
        Args:
            command_id: Unique identifier of the command
            status: New status (success, failed, timeout)
            execution_time: Time taken to execute the command
            error_message: Error message if command failed
            response_data: Response data from the device
        """
        with self._lock:
            # Find and update command in memory
            for entry in reversed(self.command_log):
                if entry.command_id == command_id:
                    entry.status = status
                    entry.execution_time = execution_time
                    entry.error_message = error_message
                    entry.response_data = response_data
                    
                    # Write updated entry to file
                    self._write_command_to_file(entry)
                    break
        
        logger.info(f"Command {command_id} status updated to: {status}")
    
    def get_command_history(self, device_id: Optional[str] = None, 
                          limit: Optional[int] = None,
                          status_filter: Optional[str] = None) -> List[CommandLogEntry]:
        """
        Get command history with optional filtering.
        
        Args:
            device_id: Filter by specific device ID
            limit: Maximum number of entries to return
            status_filter: Filter by command status
        
        Returns:
            List of CommandLogEntry objects
        """
        with self._lock:
            filtered_log = self.command_log.copy()
            
            # Apply filters
            if device_id:
                filtered_log = [entry for entry in filtered_log if entry.device_id == device_id]
            
            if status_filter:
                filtered_log = [entry for entry in filtered_log if entry.status == status_filter]
            
            # Sort by timestamp (most recent first)
            filtered_log.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            if limit:
                filtered_log = filtered_log[:limit]
            
            return filtered_log
    
    def get_device_events(self, device_id: Optional[str] = None,
                         event_type: Optional[str] = None,
                         limit: Optional[int] = None) -> List[DeviceLogEntry]:
        """
        Get device event history with optional filtering.
        
        Args:
            device_id: Filter by specific device ID
            event_type: Filter by event type
            limit: Maximum number of entries to return
        
        Returns:
            List of DeviceLogEntry objects
        """
        with self._lock:
            filtered_log = self.device_log.copy()
            
            # Apply filters
            if device_id:
                filtered_log = [entry for entry in filtered_log if entry.device_id == device_id]
            
            if event_type:
                filtered_log = [entry for entry in filtered_log if entry.event_type == event_type]
            
            # Sort by timestamp (most recent first)
            filtered_log.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            if limit:
                filtered_log = filtered_log[:limit]
            
            return filtered_log
    
    def get_command_statistics(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get command execution statistics.
        
        Args:
            device_id: Filter statistics by specific device ID
        
        Returns:
            Dictionary containing command statistics
        """
        with self._lock:
            commands = self.command_log.copy()
            
            if device_id:
                commands = [cmd for cmd in commands if cmd.device_id == device_id]
            
            total_commands = len(commands)
            if total_commands == 0:
                return {"total_commands": 0}
            
            # Count by status
            status_counts = {}
            execution_times = []
            
            for cmd in commands:
                status_counts[cmd.status] = status_counts.get(cmd.status, 0) + 1
                if cmd.execution_time is not None:
                    execution_times.append(cmd.execution_time)
            
            # Calculate execution time statistics
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            max_execution_time = max(execution_times) if execution_times else 0
            min_execution_time = min(execution_times) if execution_times else 0
            
            return {
                "total_commands": total_commands,
                "status_counts": status_counts,
                "success_rate": status_counts.get("success", 0) / total_commands * 100,
                "average_execution_time": avg_execution_time,
                "max_execution_time": max_execution_time,
                "min_execution_time": min_execution_time,
                "device_id": device_id
            }
    
    def export_logs(self, start_timestamp: Optional[float] = None,
                   end_timestamp: Optional[float] = None,
                   format_type: str = "json") -> str:
        """
        Export logs to a file for external analysis.
        
        Args:
            start_timestamp: Start time for log export
            end_timestamp: End time for log export
            format_type: Export format (json, csv)
        
        Returns:
            Path to the exported file
        """
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_file = self.log_directory / f"export_{timestamp_str}.{format_type}"
        
        with self._lock:
            # Filter logs by timestamp
            filtered_commands = self.command_log.copy()
            filtered_devices = self.device_log.copy()
            
            if start_timestamp:
                filtered_commands = [cmd for cmd in filtered_commands if cmd.timestamp >= start_timestamp]
                filtered_devices = [dev for dev in filtered_devices if dev.timestamp >= start_timestamp]
            
            if end_timestamp:
                filtered_commands = [cmd for cmd in filtered_commands if cmd.timestamp <= end_timestamp]
                filtered_devices = [dev for dev in filtered_devices if dev.timestamp <= end_timestamp]
            
            # Export based on format
            if format_type == "json":
                export_data = {
                    "export_timestamp": datetime.now().isoformat(),
                    "command_logs": [asdict(cmd) for cmd in filtered_commands],
                    "device_logs": [asdict(dev) for dev in filtered_devices]
                }
                
                with open(export_file, 'w') as f:
                    json.dump(export_data, f, indent=2)
            
            # Add CSV export if needed in the future
        
        logger.info(f"Logs exported to: {export_file}")
        return str(export_file)
    
    def _load_existing_logs(self):
        """Load existing logs from persistent storage"""
        try:
            # Load command logs
            if self.command_log_file.exists():
                with open(self.command_log_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            entry = CommandLogEntry(**data)
                            self.command_log.append(entry)
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse command log line: {e}")
            
            # Load device logs
            if self.device_log_file.exists():
                with open(self.device_log_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            entry = DeviceLogEntry(**data)
                            self.device_log.append(entry)
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to parse device log line: {e}")
            
            logger.info(f"Loaded {len(self.command_log)} command logs and {len(self.device_log)} device logs")
        
        except Exception as e:
            logger.error(f"Failed to load existing logs: {e}")
    
    def _write_command_to_file(self, command_entry: CommandLogEntry):
        """Write a command log entry to persistent storage"""
        try:
            with open(self.command_log_file, 'a') as f:
                f.write(json.dumps(asdict(command_entry)) + '\n')
        except Exception as e:
            logger.error(f"Failed to write command log to file: {e}")
    
    def _write_device_event_to_file(self, device_entry: DeviceLogEntry):
        """Write a device event log entry to persistent storage"""
        try:
            with open(self.device_log_file, 'a') as f:
                f.write(json.dumps(asdict(device_entry)) + '\n')
        except Exception as e:
            logger.error(f"Failed to write device log to file: {e}")


# Global logger instance
_command_logger = None


def get_command_logger(log_directory: str = "/tmp/collision_logs") -> CommandLogger:
    """
    Get the global command logger instance.
    
    Args:
        log_directory: Directory path for storing log files
    
    Returns:
        CommandLogger instance
    """
    global _command_logger
    if _command_logger is None:
        _command_logger = CommandLogger(log_directory)
    return _command_logger