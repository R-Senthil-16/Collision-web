"""
System-wide monitoring and logging for the Collision Detection System
"""
import os
import time
import json
import psutil
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import deque, defaultdict


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    process_count: int
    temperature: Optional[float] = None


@dataclass
class ComponentStatus:
    """Status of individual system components"""
    component_name: str
    status: str  # 'healthy', 'warning', 'error', 'offline'
    last_update: float
    metrics: Dict[str, Any]
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class PerformanceAlert:
    """Performance alert information"""
    alert_id: str
    component: str
    severity: str  # 'info', 'warning', 'error', 'critical'
    message: str
    timestamp: float
    resolved: bool = False
    resolution_time: Optional[float] = None


class SystemMonitor:
    """Comprehensive system monitoring and logging"""
    
    def __init__(self, log_directory: str = "/tmp/collision_logs"):
        self.log_directory = log_directory
        self.running = False
        self.monitor_thread = None
        
        # Metrics storage
        self.metrics_history = deque(maxlen=1000)  # Last 1000 measurements
        self.component_status = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=500)
        
        # Performance thresholds
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'temperature': 70.0,
            'response_time': 5.0
        }
        
        # Component tracking
        self.components = [
            'video_processor',
            'computer_vision',
            'collision_engine',
            'hardware_controller',
            'web_server',
            'websocket_server'
        ]
        
        # Initialize logging
        self.setup_logging()
        
        # Initialize component status
        for component in self.components:
            self.component_status[component] = ComponentStatus(
                component_name=component,
                status='offline',
                last_update=time.time(),
                metrics={}
            )
        
        self.logger.info("SystemMonitor initialized")
    
    def setup_logging(self):
        """Setup comprehensive logging configuration"""
        os.makedirs(self.log_directory, exist_ok=True)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # System monitor logger
        self.logger = logging.getLogger('system_monitor')
        self.logger.setLevel(logging.INFO)
        
        # System log file handler
        system_handler = logging.FileHandler(
            os.path.join(self.log_directory, 'system.log')
        )
        system_handler.setFormatter(detailed_formatter)
        system_handler.setLevel(logging.INFO)
        self.logger.addHandler(system_handler)
        
        # Performance log file handler
        self.perf_logger = logging.getLogger('performance')
        self.perf_logger.setLevel(logging.INFO)
        
        perf_handler = logging.FileHandler(
            os.path.join(self.log_directory, 'performance.log')
        )
        perf_handler.setFormatter(simple_formatter)
        self.perf_logger.addHandler(perf_handler)
        
        # Error log file handler
        self.error_logger = logging.getLogger('errors')
        self.error_logger.setLevel(logging.ERROR)
        
        error_handler = logging.FileHandler(
            os.path.join(self.log_directory, 'errors.log')
        )
        error_handler.setFormatter(detailed_formatter)
        self.error_logger.addHandler(error_handler)
        
        # Alert log file handler
        self.alert_logger = logging.getLogger('alerts')
        self.alert_logger.setLevel(logging.WARNING)
        
        alert_handler = logging.FileHandler(
            os.path.join(self.log_directory, 'alerts.log')
        )
        alert_handler.setFormatter(detailed_formatter)
        self.alert_logger.addHandler(alert_handler)
    
    def start(self):
        """Start system monitoring"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("System monitoring started")
    
    def stop(self):
        """Stop system monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("System monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Collect system metrics
                metrics = self._collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # Check thresholds and generate alerts
                self._check_thresholds(metrics)
                
                # Log performance metrics
                self._log_performance_metrics(metrics)
                
                # Update component status
                self._update_component_status()
                
                # Clean up old alerts
                self._cleanup_old_alerts()
                
                time.sleep(10)  # Monitor every 10 seconds
                
            except Exception as e:
                self.error_logger.error(f"Monitoring loop error: {e}")
                time.sleep(5)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            # Process count
            process_count = len(psutil.pids())
            
            # Temperature (if available)
            temperature = None
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get CPU temperature if available
                    for name, entries in temps.items():
                        if entries:
                            temperature = entries[0].current
                            break
            except:
                pass
            
            return SystemMetrics(
                timestamp=time.time(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                process_count=process_count,
                temperature=temperature
            )
            
        except Exception as e:
            self.error_logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                timestamp=time.time(),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={},
                process_count=0
            )
    
    def _check_thresholds(self, metrics: SystemMetrics):
        """Check metrics against thresholds and generate alerts"""
        current_time = time.time()
        
        # CPU usage check
        if metrics.cpu_usage > self.thresholds['cpu_usage']:
            self._create_alert(
                'cpu_high',
                'system',
                'warning',
                f'High CPU usage: {metrics.cpu_usage:.1f}%'
            )
        
        # Memory usage check
        if metrics.memory_usage > self.thresholds['memory_usage']:
            self._create_alert(
                'memory_high',
                'system',
                'warning',
                f'High memory usage: {metrics.memory_usage:.1f}%'
            )
        
        # Disk usage check
        if metrics.disk_usage > self.thresholds['disk_usage']:
            self._create_alert(
                'disk_high',
                'system',
                'error',
                f'High disk usage: {metrics.disk_usage:.1f}%'
            )
        
        # Temperature check
        if metrics.temperature and metrics.temperature > self.thresholds['temperature']:
            self._create_alert(
                'temperature_high',
                'system',
                'warning',
                f'High temperature: {metrics.temperature:.1f}°C'
            )
    
    def _create_alert(self, alert_id: str, component: str, severity: str, message: str):
        """Create a new alert"""
        # Check if alert already exists and is recent
        if alert_id in self.active_alerts:
            last_alert = self.active_alerts[alert_id]
            if time.time() - last_alert.timestamp < 300:  # Don't spam alerts within 5 minutes
                return
        
        alert = PerformanceAlert(
            alert_id=alert_id,
            component=component,
            severity=severity,
            message=message,
            timestamp=time.time()
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Log the alert
        log_message = f"ALERT [{severity.upper()}] {component}: {message}"
        if severity == 'critical':
            self.alert_logger.critical(log_message)
        elif severity == 'error':
            self.alert_logger.error(log_message)
        elif severity == 'warning':
            self.alert_logger.warning(log_message)
        else:
            self.alert_logger.info(log_message)
    
    def _log_performance_metrics(self, metrics: SystemMetrics):
        """Log performance metrics"""
        self.perf_logger.info(
            f"CPU: {metrics.cpu_usage:.1f}% | "
            f"Memory: {metrics.memory_usage:.1f}% | "
            f"Disk: {metrics.disk_usage:.1f}% | "
            f"Processes: {metrics.process_count} | "
            f"Temp: {metrics.temperature:.1f}°C" if metrics.temperature else "Temp: N/A"
        )
    
    def _update_component_status(self):
        """Update status of system components"""
        current_time = time.time()
        
        for component_name, status in self.component_status.items():
            # Check if component has been updated recently
            if current_time - status.last_update > 60:  # 1 minute timeout
                if status.status != 'offline':
                    status.status = 'offline'
                    self.logger.warning(f"Component {component_name} appears to be offline")
    
    def _cleanup_old_alerts(self):
        """Clean up resolved and old alerts"""
        current_time = time.time()
        
        # Remove alerts older than 1 hour
        alerts_to_remove = []
        for alert_id, alert in self.active_alerts.items():
            if current_time - alert.timestamp > 3600:  # 1 hour
                alerts_to_remove.append(alert_id)
        
        for alert_id in alerts_to_remove:
            del self.active_alerts[alert_id]
    
    def update_component_status(self, component_name: str, status: str, metrics: Dict[str, Any] = None):
        """Update status of a specific component"""
        if component_name not in self.component_status:
            self.component_status[component_name] = ComponentStatus(
                component_name=component_name,
                status=status,
                last_update=time.time(),
                metrics=metrics or {}
            )
        else:
            component = self.component_status[component_name]
            old_status = component.status
            component.status = status
            component.last_update = time.time()
            component.metrics = metrics or {}
            
            # Log status changes
            if old_status != status:
                self.logger.info(f"Component {component_name} status changed: {old_status} -> {status}")
    
    def log_component_error(self, component_name: str, error_message: str):
        """Log an error for a specific component"""
        if component_name in self.component_status:
            component = self.component_status[component_name]
            component.error_count += 1
            component.last_error = error_message
            
            self.error_logger.error(f"Component {component_name}: {error_message}")
            
            # Create alert for component errors
            self._create_alert(
                f'{component_name}_error',
                component_name,
                'error',
                f'Component error: {error_message}'
            )
    
    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive system health summary"""
        if not self.metrics_history:
            return {'status': 'no_data', 'message': 'No metrics available'}
        
        latest_metrics = self.metrics_history[-1]
        
        # Calculate averages over last 10 minutes
        recent_metrics = [m for m in self.metrics_history if time.time() - m.timestamp < 600]
        
        if recent_metrics:
            avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
            avg_disk = sum(m.disk_usage for m in recent_metrics) / len(recent_metrics)
        else:
            avg_cpu = latest_metrics.cpu_usage
            avg_memory = latest_metrics.memory_usage
            avg_disk = latest_metrics.disk_usage
        
        # Determine overall health status
        health_status = 'healthy'
        if (avg_cpu > self.thresholds['cpu_usage'] or 
            avg_memory > self.thresholds['memory_usage'] or 
            avg_disk > self.thresholds['disk_usage']):
            health_status = 'warning'
        
        if len(self.active_alerts) > 0:
            critical_alerts = [a for a in self.active_alerts.values() if a.severity == 'critical']
            error_alerts = [a for a in self.active_alerts.values() if a.severity == 'error']
            
            if critical_alerts:
                health_status = 'critical'
            elif error_alerts:
                health_status = 'error'
        
        # Component health summary
        component_health = {}
        for name, status in self.component_status.items():
            component_health[name] = {
                'status': status.status,
                'last_update': status.last_update,
                'error_count': status.error_count,
                'last_error': status.last_error
            }
        
        return {
            'overall_status': health_status,
            'timestamp': latest_metrics.timestamp,
            'system_metrics': {
                'cpu_usage': latest_metrics.cpu_usage,
                'memory_usage': latest_metrics.memory_usage,
                'disk_usage': latest_metrics.disk_usage,
                'temperature': latest_metrics.temperature,
                'process_count': latest_metrics.process_count
            },
            'averages': {
                'cpu_usage': avg_cpu,
                'memory_usage': avg_memory,
                'disk_usage': avg_disk
            },
            'component_health': component_health,
            'active_alerts': len(self.active_alerts),
            'alert_summary': {
                'critical': len([a for a in self.active_alerts.values() if a.severity == 'critical']),
                'error': len([a for a in self.active_alerts.values() if a.severity == 'error']),
                'warning': len([a for a in self.active_alerts.values() if a.severity == 'warning']),
                'info': len([a for a in self.active_alerts.values() if a.severity == 'info'])
            }
        }
    
    def get_performance_history(self, duration_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get performance history for specified duration"""
        cutoff_time = time.time() - (duration_minutes * 60)
        
        history = []
        for metrics in self.metrics_history:
            if metrics.timestamp >= cutoff_time:
                history.append(asdict(metrics))
        
        return history
    
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alert history"""
        alerts = list(self.alert_history)[-limit:]
        return [asdict(alert) for alert in alerts]
    
    def get_component_metrics(self, component_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific component"""
        if component_name in self.component_status:
            return asdict(self.component_status[component_name])
        return None
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolution_time = time.time()
            
            self.logger.info(f"Alert {alert_id} manually resolved")
            del self.active_alerts[alert_id]
            return True
        
        return False
    
    def set_threshold(self, metric: str, value: float):
        """Update performance threshold"""
        if metric in self.thresholds:
            old_value = self.thresholds[metric]
            self.thresholds[metric] = value
            self.logger.info(f"Threshold for {metric} updated: {old_value} -> {value}")
    
    def get_log_files(self) -> Dict[str, str]:
        """Get paths to all log files"""
        return {
            'system': os.path.join(self.log_directory, 'system.log'),
            'performance': os.path.join(self.log_directory, 'performance.log'),
            'errors': os.path.join(self.log_directory, 'errors.log'),
            'alerts': os.path.join(self.log_directory, 'alerts.log')
        }
    
    def get_log_tail(self, log_type: str, lines: int = 100) -> List[str]:
        """Get last N lines from a specific log file"""
        log_files = self.get_log_files()
        
        if log_type not in log_files:
            return []
        
        log_file = log_files[log_type]
        
        if not os.path.exists(log_file):
            return []
        
        try:
            with open(log_file, 'r') as f:
                return f.readlines()[-lines:]
        except Exception as e:
            self.error_logger.error(f"Failed to read log file {log_file}: {e}")
            return []