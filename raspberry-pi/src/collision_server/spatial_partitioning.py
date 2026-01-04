"""
Spatial Partitioning System for Optimized Collision Detection

Requirements covered:
- 6.2: Use efficient algorithms to minimize computational overhead
- 6.3: Optimize rendering by only updating changed areas when possible
"""
import math
import time
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class BoundingBox:
    """Bounding box representation for spatial partitioning"""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if this bounding box intersects with another"""
        return not (self.x + self.width < other.x or 
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or 
                   other.y + other.height < self.y)
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is inside this bounding box"""
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)


@dataclass
class SpatialObject:
    """Object with spatial information for partitioning"""
    id: str
    bbox: BoundingBox
    data: Any  # Additional object data
    last_updated: float = 0.0


class SpatialGrid:
    """Grid-based spatial partitioning for efficient collision detection"""
    
    def __init__(self, width: float, height: float, cell_size: float = 100.0):
        """
        Initialize spatial grid
        
        Args:
            width: Total width of the spatial area
            height: Total height of the spatial area
            cell_size: Size of each grid cell (smaller = more precise, larger = less memory)
        """
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.cols = math.ceil(width / cell_size)
        self.rows = math.ceil(height / cell_size)
        
        # Grid cells containing object IDs
        self.grid: Dict[Tuple[int, int], Set[str]] = defaultdict(set)
        
        # Object storage
        self.objects: Dict[str, SpatialObject] = {}
        
        # Performance tracking
        self.stats = {
            'total_objects': 0,
            'collision_checks': 0,
            'grid_updates': 0,
            'last_update_time': 0.0,
            'average_objects_per_cell': 0.0
        }
    
    def _get_cell_coords(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coordinates to grid cell coordinates"""
        col = max(0, min(self.cols - 1, int(x / self.cell_size)))
        row = max(0, min(self.rows - 1, int(y / self.cell_size)))
        return (col, row)
    
    def _get_cells_for_bbox(self, bbox: BoundingBox) -> List[Tuple[int, int]]:
        """Get all grid cells that a bounding box overlaps"""
        min_col, min_row = self._get_cell_coords(bbox.x, bbox.y)
        max_col, max_row = self._get_cell_coords(bbox.x + bbox.width, bbox.y + bbox.height)
        
        cells = []
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                cells.append((col, row))
        
        return cells
    
    def add_object(self, obj_id: str, bbox: BoundingBox, data: Any = None):
        """Add or update an object in the spatial grid"""
        current_time = time.time()
        
        # Remove object from old cells if it exists
        if obj_id in self.objects:
            self.remove_object(obj_id)
        
        # Create spatial object
        spatial_obj = SpatialObject(
            id=obj_id,
            bbox=bbox,
            data=data,
            last_updated=current_time
        )
        
        # Add to object storage
        self.objects[obj_id] = spatial_obj
        
        # Add to appropriate grid cells
        cells = self._get_cells_for_bbox(bbox)
        for cell in cells:
            self.grid[cell].add(obj_id)
        
        # Update statistics
        self.stats['total_objects'] = len(self.objects)
        self.stats['grid_updates'] += 1
        self.stats['last_update_time'] = current_time
        self._update_cell_statistics()
    
    def remove_object(self, obj_id: str):
        """Remove an object from the spatial grid"""
        if obj_id not in self.objects:
            return
        
        spatial_obj = self.objects[obj_id]
        
        # Remove from all grid cells
        cells = self._get_cells_for_bbox(spatial_obj.bbox)
        for cell in cells:
            self.grid[cell].discard(obj_id)
            # Clean up empty cells
            if not self.grid[cell]:
                del self.grid[cell]
        
        # Remove from object storage
        del self.objects[obj_id]
        
        # Update statistics
        self.stats['total_objects'] = len(self.objects)
        self._update_cell_statistics()
    
    def update_object(self, obj_id: str, new_bbox: BoundingBox, data: Any = None):
        """Update an object's position and data"""
        self.add_object(obj_id, new_bbox, data)
    
    def get_nearby_objects(self, bbox: BoundingBox) -> List[SpatialObject]:
        """Get all objects that could potentially collide with the given bounding box"""
        nearby_ids = set()
        
        # Get all cells that the bounding box overlaps
        cells = self._get_cells_for_bbox(bbox)
        
        # Collect all object IDs from those cells
        for cell in cells:
            if cell in self.grid:
                nearby_ids.update(self.grid[cell])
        
        # Return the actual objects
        return [self.objects[obj_id] for obj_id in nearby_ids if obj_id in self.objects]
    
    def find_collisions(self, obj_id: str) -> List[SpatialObject]:
        """Find all objects that collide with the specified object"""
        if obj_id not in self.objects:
            return []
        
        target_obj = self.objects[obj_id]
        nearby_objects = self.get_nearby_objects(target_obj.bbox)
        
        collisions = []
        for other_obj in nearby_objects:
            if other_obj.id != obj_id and target_obj.bbox.intersects(other_obj.bbox):
                collisions.append(other_obj)
                self.stats['collision_checks'] += 1
        
        return collisions
    
    def find_all_collisions(self) -> List[Tuple[SpatialObject, SpatialObject]]:
        """Find all collision pairs in the grid"""
        collision_pairs = []
        checked_pairs = set()
        
        for obj_id, obj in self.objects.items():
            nearby_objects = self.get_nearby_objects(obj.bbox)
            
            for other_obj in nearby_objects:
                if other_obj.id != obj_id:
                    # Create a consistent pair identifier to avoid duplicates
                    pair_id = tuple(sorted([obj_id, other_obj.id]))
                    
                    if pair_id not in checked_pairs and obj.bbox.intersects(other_obj.bbox):
                        collision_pairs.append((obj, other_obj))
                        checked_pairs.add(pair_id)
                        self.stats['collision_checks'] += 1
        
        return collision_pairs
    
    def get_objects_in_region(self, region_bbox: BoundingBox) -> List[SpatialObject]:
        """Get all objects within a specific region"""
        objects_in_region = []
        nearby_objects = self.get_nearby_objects(region_bbox)
        
        for obj in nearby_objects:
            if region_bbox.intersects(obj.bbox):
                objects_in_region.append(obj)
        
        return objects_in_region
    
    def clear(self):
        """Clear all objects from the grid"""
        self.grid.clear()
        self.objects.clear()
        self.stats['total_objects'] = 0
        self._update_cell_statistics()
    
    def _update_cell_statistics(self):
        """Update statistics about grid cell usage"""
        if not self.grid:
            self.stats['average_objects_per_cell'] = 0.0
            return
        
        total_objects_in_cells = sum(len(cell_objects) for cell_objects in self.grid.values())
        self.stats['average_objects_per_cell'] = total_objects_in_cells / len(self.grid)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the spatial grid"""
        return {
            **self.stats,
            'grid_dimensions': (self.cols, self.rows),
            'cell_size': self.cell_size,
            'total_cells': self.cols * self.rows,
            'active_cells': len(self.grid),
            'cell_utilization': len(self.grid) / (self.cols * self.rows) if self.cols * self.rows > 0 else 0.0
        }
    
    def optimize_cell_size(self, target_objects_per_cell: float = 5.0):
        """
        Automatically optimize cell size based on current object distribution
        
        Args:
            target_objects_per_cell: Target average number of objects per cell
        """
        if self.stats['total_objects'] == 0:
            return
        
        current_avg = self.stats['average_objects_per_cell']
        
        # If we have too many objects per cell, make cells smaller
        if current_avg > target_objects_per_cell * 1.5:
            new_cell_size = self.cell_size * 0.8
        # If we have too few objects per cell, make cells larger
        elif current_avg < target_objects_per_cell * 0.5:
            new_cell_size = self.cell_size * 1.2
        else:
            return  # Cell size is already optimal
        
        # Rebuild grid with new cell size
        old_objects = list(self.objects.values())
        self.cell_size = max(10.0, min(500.0, new_cell_size))  # Clamp to reasonable range
        self.cols = math.ceil(self.width / self.cell_size)
        self.rows = math.ceil(self.height / self.cell_size)
        
        # Clear and rebuild
        self.clear()
        for obj in old_objects:
            self.add_object(obj.id, obj.bbox, obj.data)


class PerformanceMonitor:
    """Monitor and track collision detection performance"""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize performance monitor
        
        Args:
            window_size: Number of recent measurements to keep for averaging
        """
        self.window_size = window_size
        self.frame_times = []
        self.collision_counts = []
        self.object_counts = []
        self.timestamps = []
        
        # Performance thresholds
        self.target_fps = 30.0
        self.max_frame_time = 1.0 / self.target_fps
        
        # Quality adjustment parameters
        self.quality_level = 1.0  # 1.0 = full quality, 0.5 = half quality, etc.
        self.min_quality = 0.25
        self.max_quality = 1.0
    
    def record_frame(self, frame_time: float, collision_count: int, object_count: int):
        """Record performance data for a frame"""
        current_time = time.time()
        
        self.frame_times.append(frame_time)
        self.collision_counts.append(collision_count)
        self.object_counts.append(object_count)
        self.timestamps.append(current_time)
        
        # Keep only recent measurements
        if len(self.frame_times) > self.window_size:
            self.frame_times.pop(0)
            self.collision_counts.pop(0)
            self.object_counts.pop(0)
            self.timestamps.pop(0)
    
    def get_average_fps(self) -> float:
        """Get average FPS over the measurement window"""
        if not self.frame_times:
            return 0.0
        
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get comprehensive performance metrics"""
        if not self.frame_times:
            return {
                'average_fps': 0.0,
                'average_frame_time': 0.0,
                'average_collisions': 0.0,
                'average_objects': 0.0,
                'quality_level': self.quality_level
            }
        
        return {
            'average_fps': self.get_average_fps(),
            'average_frame_time': sum(self.frame_times) / len(self.frame_times),
            'average_collisions': sum(self.collision_counts) / len(self.collision_counts),
            'average_objects': sum(self.object_counts) / len(self.object_counts),
            'quality_level': self.quality_level,
            'target_fps': self.target_fps,
            'performance_ratio': self.get_average_fps() / self.target_fps
        }
    
    def should_adjust_quality(self) -> bool:
        """Check if quality adjustment is needed based on performance"""
        if len(self.frame_times) < 10:  # Need enough samples
            return False
        
        avg_fps = self.get_average_fps()
        
        # Adjust quality if performance is significantly off target
        if avg_fps < self.target_fps * 0.8:  # Performance too low
            return True
        elif avg_fps > self.target_fps * 1.2 and self.quality_level < self.max_quality:  # Performance too high, can increase quality
            return True
        
        return False
    
    def adjust_quality(self) -> float:
        """
        Automatically adjust quality level based on performance
        
        Returns:
            New quality level
        """
        if not self.should_adjust_quality():
            return self.quality_level
        
        avg_fps = self.get_average_fps()
        performance_ratio = avg_fps / self.target_fps
        
        if performance_ratio < 0.8:  # Performance too low, reduce quality
            self.quality_level = max(self.min_quality, self.quality_level * 0.9)
        elif performance_ratio > 1.2:  # Performance too high, increase quality
            self.quality_level = min(self.max_quality, self.quality_level * 1.1)
        
        return self.quality_level
    
    def get_quality_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for quality adjustments"""
        metrics = self.get_performance_metrics()
        recommendations = []
        
        if metrics['average_fps'] < self.target_fps * 0.8:
            recommendations.append("Reduce collision detection precision")
            recommendations.append("Increase spatial grid cell size")
            recommendations.append("Reduce object tracking accuracy")
        
        if metrics['average_objects'] > 50:
            recommendations.append("Implement object culling for distant objects")
            recommendations.append("Use level-of-detail for object processing")
        
        if metrics['average_collisions'] > 20:
            recommendations.append("Optimize collision response calculations")
            recommendations.append("Batch collision processing")
        
        return {
            'current_performance': metrics,
            'recommendations': recommendations,
            'suggested_quality': self.adjust_quality()
        }


# Export classes for module use
__all__ = ['BoundingBox', 'SpatialObject', 'SpatialGrid', 'PerformanceMonitor']


# Example usage and testing
if __name__ == "__main__":
    print("Testing Spatial Partitioning System...")
    
    # Create a spatial grid
    grid = SpatialGrid(1000, 1000, 50)
    
    # Add some test objects
    grid.add_object("obj1", BoundingBox(100, 100, 50, 50), {"type": "vehicle"})
    grid.add_object("obj2", BoundingBox(120, 120, 30, 30), {"type": "person"})
    grid.add_object("obj3", BoundingBox(500, 500, 40, 40), {"type": "ball"})
    
    # Find collisions
    collisions = grid.find_all_collisions()
    print(f"Found {len(collisions)} collision pairs")
    
    # Test performance monitoring
    monitor = PerformanceMonitor()
    
    # Simulate some frame processing
    for i in range(50):
        frame_time = 0.02 + (i % 10) * 0.005  # Varying frame times
        collision_count = len(collisions)
        object_count = len(grid.objects)
        
        monitor.record_frame(frame_time, collision_count, object_count)
    
    # Get performance metrics
    metrics = monitor.get_performance_metrics()
    print(f"Average FPS: {metrics['average_fps']:.2f}")
    print(f"Quality Level: {metrics['quality_level']:.2f}")
    
    # Get grid statistics
    stats = grid.get_performance_stats()
    print(f"Grid utilization: {stats['cell_utilization']:.2%}")
    print(f"Average objects per cell: {stats['average_objects_per_cell']:.2f}")
    
    print("Spatial Partitioning System test completed successfully!")