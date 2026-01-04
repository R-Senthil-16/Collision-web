"""
Resource Management and Prioritization System

Requirements covered:
- 11.4: Prioritize real-time processing over uploaded video analysis
- 6.1: Maintain at least 30 FPS with efficient resource allocation
"""
import threading
import time
import psutil
import queue
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum, IntEnum
from collections import defaultdict


class TaskPriority(IntEnum):
    """Task priority levels (higher number = higher priority)"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    REAL_TIME = 5


class ResourceType(Enum):
    """System resource types"""
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    DISK_IO = "disk_io"
    NETWORK = "network"


@dataclass
class ResourceLimits:
    """Resource usage limits for different task types"""
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 70.0
    max_concurrent_tasks: int = 4
    real_time_cpu_reserve: float = 30.0  # Reserve 30% CPU for real-time tasks
    real_time_memory_reserve: float = 20.0  # Reserve 20% memory for real-time tasks


@dataclass
class ProcessingTask:
    """Processing task with priority and resource requirements"""
    task_id: str
    task_type: str
    priority: TaskPriority
    callback: Callable
    args: tuple
    kwargs: dict
    estimated_cpu_usage: float = 25.0
    estimated_memory_mb: float = 100.0
    estimated_duration: float = 10.0
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class SystemResources:
    """Current system resource usage"""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_io_percent: float
    active_tasks: int
    real_time_tasks: int
    timestamp: datetime


class ResourceManager:
    """Manages system resources and task prioritization"""
    
    def __init__(self, limits: ResourceLimits = None):
        """
        Initialize resource manager
        
        Args:
            limits: Resource usage limits configuration
        """
        self.limits = limits or ResourceLimits()
        self.task_queue = queue.PriorityQueue()
        self.active_tasks: Dict[str, ProcessingTask] = {}
        self.completed_tasks: Dict[str, ProcessingTask] = {}
        self.task_threads: Dict[str, threading.Thread] = {}
        
        # Resource monitoring
        self.current_resources = SystemResources(0, 0, 0, 0, 0, 0, datetime.utcnow())
        self.resource_history: List[SystemResources] = []
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_stop_flag = threading.Event()
        
        # Task execution control
        self.execution_thread: Optional[threading.Thread] = None
        self.execution_stop_flag = threading.Event()
        
        # Statistics
        self.task_stats = defaultdict(lambda: {
            'total': 0, 'completed': 0, 'failed': 0, 
            'avg_duration': 0.0, 'avg_cpu': 0.0, 'avg_memory': 0.0
        })
        
        self._lock = threading.RLock()
    
    def start(self):
        """Start resource monitoring and task execution"""
        with self._lock:
            if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
                self.monitoring_stop_flag.clear()
                self.monitoring_thread = threading.Thread(
                    target=self._monitor_resources,
                    daemon=True
                )
                self.monitoring_thread.start()
            
            if self.execution_thread is None or not self.execution_thread.is_alive():
                self.execution_stop_flag.clear()
                self.execution_thread = threading.Thread(
                    target=self._execute_tasks,
                    daemon=True
                )
                self.execution_thread.start()
    
    def stop(self):
        """Stop resource monitoring and task execution"""
        with self._lock:
            self.monitoring_stop_flag.set()
            self.execution_stop_flag.set()
            
            # Wait for threads to finish
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5.0)
            
            if self.execution_thread and self.execution_thread.is_alive():
                self.execution_thread.join(timeout=5.0)
            
            # Cancel remaining tasks
            self._cancel_all_tasks()
    
    def submit_task(self, task: ProcessingTask) -> bool:
        """
        Submit a task for execution
        
        Args:
            task: Processing task to submit
            
        Returns:
            True if task was accepted, False if rejected due to resource constraints
        """
        with self._lock:
            # Check if we can accept this task based on current resources
            if not self._can_accept_task(task):
                return False
            
            # Add task to priority queue (negative priority for correct ordering)
            priority_score = self._calculate_priority_score(task)
            self.task_queue.put((-priority_score, task.created_at, task))
            
            # Update statistics
            self.task_stats[task.task_type]['total'] += 1
            
            return True
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending or active task
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled, False if not found or already completed
        """
        with self._lock:
            # Check if task is active
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                
                # Mark task as cancelled
                task.completed_at = datetime.utcnow()
                
                # Move to completed tasks
                self.completed_tasks[task_id] = task
                del self.active_tasks[task_id]
                
                # Stop thread if it exists
                if task_id in self.task_threads:
                    # Note: We can't forcefully stop threads in Python
                    # The task callback should check for cancellation
                    del self.task_threads[task_id]
                
                return True
            
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status and resource usage
        
        Returns:
            Dictionary with system status information
        """
        with self._lock:
            return {
                'resources': {
                    'cpu_percent': self.current_resources.cpu_percent,
                    'memory_percent': self.current_resources.memory_percent,
                    'memory_available_mb': self.current_resources.memory_available_mb,
                    'disk_io_percent': self.current_resources.disk_io_percent,
                    'timestamp': self.current_resources.timestamp.isoformat()
                },
                'tasks': {
                    'active': len(self.active_tasks),
                    'real_time': self.current_resources.real_time_tasks,
                    'queued': self.task_queue.qsize(),
                    'completed': len(self.completed_tasks)
                },
                'limits': {
                    'max_cpu_percent': self.limits.max_cpu_percent,
                    'max_memory_percent': self.limits.max_memory_percent,
                    'max_concurrent_tasks': self.limits.max_concurrent_tasks,
                    'real_time_cpu_reserve': self.limits.real_time_cpu_reserve,
                    'real_time_memory_reserve': self.limits.real_time_memory_reserve
                },
                'statistics': dict(self.task_stats)
            }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific task
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status dictionary or None if not found
        """
        with self._lock:
            task = None
            status = "unknown"
            
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                status = "active"
            elif task_id in self.completed_tasks:
                task = self.completed_tasks[task_id]
                status = "completed"
            else:
                # Check if task is in queue
                temp_queue = []
                found = False
                
                while not self.task_queue.empty():
                    priority, created_at, queued_task = self.task_queue.get()
                    temp_queue.append((priority, created_at, queued_task))
                    
                    if queued_task.task_id == task_id:
                        task = queued_task
                        status = "queued"
                        found = True
                
                # Restore queue
                for item in temp_queue:
                    self.task_queue.put(item)
                
                if not found:
                    return None
            
            return {
                'task_id': task.task_id,
                'task_type': task.task_type,
                'priority': task.priority.name,
                'status': status,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'estimated_cpu_usage': task.estimated_cpu_usage,
                'estimated_memory_mb': task.estimated_memory_mb,
                'estimated_duration': task.estimated_duration
            }
    
    def update_limits(self, new_limits: ResourceLimits):
        """
        Update resource limits
        
        Args:
            new_limits: New resource limits configuration
        """
        with self._lock:
            self.limits = new_limits
    
    def _monitor_resources(self):
        """Monitor system resources in background thread"""
        while not self.monitoring_stop_flag.is_set():
            try:
                # Get current system resources
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk_io = psutil.disk_io_counters()
                
                # Calculate disk I/O percentage (simplified)
                disk_io_percent = min((disk_io.read_bytes + disk_io.write_bytes) / (1024 * 1024 * 100), 100.0) if disk_io else 0.0
                
                # Count real-time tasks
                real_time_tasks = sum(1 for task in self.active_tasks.values() 
                                    if task.priority == TaskPriority.REAL_TIME)
                
                # Update current resources
                with self._lock:
                    self.current_resources = SystemResources(
                        cpu_percent=cpu_percent,
                        memory_percent=memory.percent,
                        memory_available_mb=memory.available / (1024 * 1024),
                        disk_io_percent=disk_io_percent,
                        active_tasks=len(self.active_tasks),
                        real_time_tasks=real_time_tasks,
                        timestamp=datetime.utcnow()
                    )
                    
                    # Keep resource history (last 100 entries)
                    self.resource_history.append(self.current_resources)
                    if len(self.resource_history) > 100:
                        self.resource_history.pop(0)
                
                time.sleep(1.0)  # Monitor every second
                
            except Exception as e:
                print(f"Resource monitoring error: {e}")
                time.sleep(5.0)  # Wait longer on error
    
    def _execute_tasks(self):
        """Execute tasks from priority queue"""
        while not self.execution_stop_flag.is_set():
            try:
                # Get next task from queue (with timeout)
                try:
                    priority, created_at, task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Check if we can execute this task now
                if not self._can_execute_task(task):
                    # Put task back in queue and wait
                    self.task_queue.put((priority, created_at, task))
                    time.sleep(0.5)
                    continue
                
                # Start task execution
                with self._lock:
                    task.started_at = datetime.utcnow()
                    self.active_tasks[task.task_id] = task
                
                # Execute task in separate thread
                thread = threading.Thread(
                    target=self._execute_task_wrapper,
                    args=(task,),
                    daemon=True
                )
                
                with self._lock:
                    self.task_threads[task.task_id] = thread
                
                thread.start()
                
            except Exception as e:
                print(f"Task execution error: {e}")
                time.sleep(1.0)
    
    def _execute_task_wrapper(self, task: ProcessingTask):
        """Wrapper for task execution with error handling and cleanup"""
        try:
            # Execute the task
            result = task.callback(*task.args, **task.kwargs)
            
            # Mark task as completed
            with self._lock:
                task.completed_at = datetime.utcnow()
                
                # Update statistics
                duration = (task.completed_at - task.started_at).total_seconds()
                stats = self.task_stats[task.task_type]
                stats['completed'] += 1
                
                # Update averages
                total_completed = stats['completed']
                stats['avg_duration'] = ((stats['avg_duration'] * (total_completed - 1)) + duration) / total_completed
                stats['avg_cpu'] = ((stats['avg_cpu'] * (total_completed - 1)) + task.estimated_cpu_usage) / total_completed
                stats['avg_memory'] = ((stats['avg_memory'] * (total_completed - 1)) + task.estimated_memory_mb) / total_completed
                
                # Move task to completed
                self.completed_tasks[task.task_id] = task
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
                if task.task_id in self.task_threads:
                    del self.task_threads[task.task_id]
        
        except Exception as e:
            print(f"Task {task.task_id} failed: {e}")
            
            with self._lock:
                task.completed_at = datetime.utcnow()
                
                # Update failure statistics
                self.task_stats[task.task_type]['failed'] += 1
                
                # Move task to completed (with error)
                self.completed_tasks[task.task_id] = task
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
                if task.task_id in self.task_threads:
                    del self.task_threads[task.task_id]
    
    def _can_accept_task(self, task: ProcessingTask) -> bool:
        """Check if we can accept a new task based on current resources"""
        # Always accept real-time tasks (they have highest priority)
        if task.priority == TaskPriority.REAL_TIME:
            return True
        
        # Check queue size
        if self.task_queue.qsize() >= self.limits.max_concurrent_tasks * 2:
            return False
        
        # Check if we have enough reserved resources for real-time tasks
        available_cpu = 100.0 - self.limits.real_time_cpu_reserve
        available_memory = 100.0 - self.limits.real_time_memory_reserve
        
        if (self.current_resources.cpu_percent + task.estimated_cpu_usage > available_cpu or
            self.current_resources.memory_percent + (task.estimated_memory_mb / self.current_resources.memory_available_mb * 100) > available_memory):
            return False
        
        return True
    
    def _can_execute_task(self, task: ProcessingTask) -> bool:
        """Check if we can execute a task now based on current resources"""
        # Always allow real-time tasks
        if task.priority == TaskPriority.REAL_TIME:
            return len(self.active_tasks) < self.limits.max_concurrent_tasks
        
        # Check concurrent task limit
        if len(self.active_tasks) >= self.limits.max_concurrent_tasks:
            return False
        
        # Check CPU and memory limits
        if (self.current_resources.cpu_percent > self.limits.max_cpu_percent or
            self.current_resources.memory_percent > self.limits.max_memory_percent):
            return False
        
        # Ensure we maintain reserves for real-time tasks
        available_cpu = self.limits.max_cpu_percent - self.limits.real_time_cpu_reserve
        available_memory = self.limits.max_memory_percent - self.limits.real_time_memory_reserve
        
        if (self.current_resources.cpu_percent + task.estimated_cpu_usage > available_cpu or
            self.current_resources.memory_percent > available_memory):
            return False
        
        return True
    
    def _calculate_priority_score(self, task: ProcessingTask) -> float:
        """Calculate priority score for task ordering"""
        base_score = float(task.priority.value) * 1000
        
        # Add urgency based on creation time (older tasks get higher priority)
        age_minutes = (datetime.utcnow() - task.created_at).total_seconds() / 60
        urgency_score = min(age_minutes * 10, 500)  # Cap at 500 points
        
        # Subtract estimated resource usage (prefer lighter tasks when resources are constrained)
        resource_penalty = (task.estimated_cpu_usage + task.estimated_memory_mb / 100) * 5
        
        return base_score + urgency_score - resource_penalty
    
    def _cancel_all_tasks(self):
        """Cancel all pending and active tasks"""
        # Cancel active tasks
        for task_id in list(self.active_tasks.keys()):
            self.cancel_task(task_id)
        
        # Clear queue
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except queue.Empty:
                break


# Factory function for creating resource manager with different configurations
def create_resource_manager(config_type: str = "default") -> ResourceManager:
    """
    Create resource manager with predefined configuration
    
    Args:
        config_type: Configuration type ("default", "high_performance", "low_resource")
        
    Returns:
        Configured ResourceManager instance
    """
    if config_type == "high_performance":
        limits = ResourceLimits(
            max_cpu_percent=90.0,
            max_memory_percent=85.0,
            max_concurrent_tasks=6,
            real_time_cpu_reserve=20.0,
            real_time_memory_reserve=15.0
        )
    elif config_type == "low_resource":
        limits = ResourceLimits(
            max_cpu_percent=60.0,
            max_memory_percent=50.0,
            max_concurrent_tasks=2,
            real_time_cpu_reserve=40.0,
            real_time_memory_reserve=30.0
        )
    else:  # default
        limits = ResourceLimits()
    
    return ResourceManager(limits)


if __name__ == "__main__":
    # Test the resource manager
    print("Testing Resource Manager...")
    
    manager = create_resource_manager("default")
    manager.start()
    
    # Test task submission
    def test_task(task_name: str, duration: float):
        print(f"Executing {task_name} for {duration} seconds")
        time.sleep(duration)
        return f"{task_name} completed"
    
    # Submit test tasks
    task1 = ProcessingTask(
        task_id="test_1",
        task_type="video_processing",
        priority=TaskPriority.NORMAL,
        callback=test_task,
        args=("Video Processing", 2.0),
        kwargs={}
    )
    
    task2 = ProcessingTask(
        task_id="test_2",
        task_type="real_time_detection",
        priority=TaskPriority.REAL_TIME,
        callback=test_task,
        args=("Real-time Detection", 1.0),
        kwargs={}
    )
    
    print("Submitting tasks...")
    print(f"Task 1 accepted: {manager.submit_task(task1)}")
    print(f"Task 2 accepted: {manager.submit_task(task2)}")
    
    # Wait and check status
    time.sleep(5)
    print("System status:", manager.get_system_status())
    
    manager.stop()
    print("Resource Manager test completed!")