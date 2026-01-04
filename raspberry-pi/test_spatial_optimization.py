#!/usr/bin/env python3
"""
Test script for spatial partitioning optimization
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from collision_server.spatial_partitioning import SpatialGrid, PerformanceMonitor, BoundingBox

def test_spatial_partitioning():
    print('Testing Spatial Partitioning System...')
    
    # Create spatial grid
    grid = SpatialGrid(1000, 1000, 50)
    
    # Add test objects
    grid.add_object('obj1', BoundingBox(100, 100, 50, 50), {'type': 'vehicle'})
    grid.add_object('obj2', BoundingBox(120, 120, 30, 30), {'type': 'person'})
    grid.add_object('obj3', BoundingBox(500, 500, 40, 40), {'type': 'ball'})
    
    # Find collisions
    collisions = grid.find_all_collisions()
    print(f'Found {len(collisions)} collision pairs')
    
    # Test performance monitoring
    monitor = PerformanceMonitor()
    for i in range(10):
        frame_time = 0.02 + (i % 3) * 0.005
        monitor.record_frame(frame_time, len(collisions), len(grid.objects))
    
    metrics = monitor.get_performance_metrics()
    print(f'Average FPS: {metrics["average_fps"]:.2f}')
    print(f'Quality Level: {metrics["quality_level"]:.2f}')
    
    stats = grid.get_performance_stats()
    print(f'Grid utilization: {stats["cell_utilization"]:.2%}')
    print(f'Average objects per cell: {stats["average_objects_per_cell"]:.2f}')
    
    print('Spatial Partitioning System test completed successfully!')
    return True

def test_collision_engine_optimization():
    print('\nTesting Collision Engine Optimization...')
    
    try:
        from collision_server.collision_engine import CollisionEngine
        from collision_server.computer_vision import ComputerVisionModule
        
        # Create mock CV module
        class MockCVModule:
            def detect_objects(self, frame):
                return []
            
            def track_objects(self, detections, timestamp):
                return []
        
        cv_module = MockCVModule()
        engine = CollisionEngine(cv_module, frame_width=800, frame_height=600)
        
        # Test performance summary
        summary = engine.get_performance_summary()
        print(f'Spatial optimization enabled: {summary["spatial_optimization"]["enabled"]}')
        print(f'Adaptive quality enabled: {summary["quality_settings"]["adaptive_quality_enabled"]}')
        
        # Test optimization
        result = engine.optimize_performance()
        print(f'Optimization applied: {result["optimization_applied"]}')
        
        print('Collision Engine Optimization test completed successfully!')
        return True
        
    except ImportError as e:
        print(f'Could not test collision engine optimization: {e}')
        return False

if __name__ == "__main__":
    success = True
    
    try:
        success &= test_spatial_partitioning()
        success &= test_collision_engine_optimization()
        
        if success:
            print('\n✅ All optimization tests passed!')
        else:
            print('\n❌ Some optimization tests failed!')
            
    except Exception as e:
        print(f'\n❌ Test failed with error: {e}')
        success = False
    
    sys.exit(0 if success else 1)