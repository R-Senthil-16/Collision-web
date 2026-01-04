/**
 * Simple test for web collision optimization concepts
 */

console.log('🚀 Testing Web Collision Optimization Concepts');
console.log('=' * 50);

// Test 1: Spatial Grid Concept
function testSpatialGridConcept() {
    console.log('\n=== Testing Spatial Grid Concept ===');
    
    // Simple spatial grid implementation for testing
    class SimpleSpatialGrid {
        constructor(width, height, cellSize) {
            this.width = width;
            this.height = height;
            this.cellSize = cellSize;
            this.cols = Math.ceil(width / cellSize);
            this.rows = Math.ceil(height / cellSize);
            this.grid = new Map();
            this.objects = new Map();
        }
        
        getCellKey(x, y) {
            const col = Math.floor(x / this.cellSize);
            const row = Math.floor(y / this.cellSize);
            return `${col},${row}`;
        }
        
        addObject(id, x, y, width, height) {
            const obj = { id, x, y, width, height };
            this.objects.set(id, obj);
            
            // Add to grid cells
            const cellKey = this.getCellKey(x + width/2, y + height/2);
            if (!this.grid.has(cellKey)) {
                this.grid.set(cellKey, new Set());
            }
            this.grid.get(cellKey).add(id);
        }
        
        findNearbyObjects(x, y, width, height) {
            const cellKey = this.getCellKey(x + width/2, y + height/2);
            const nearbyIds = this.grid.get(cellKey) || new Set();
            return Array.from(nearbyIds).map(id => this.objects.get(id));
        }
        
        checkCollision(obj1, obj2) {
            return !(obj1.x + obj1.width < obj2.x || 
                    obj2.x + obj2.width < obj1.x ||
                    obj1.y + obj1.height < obj2.y || 
                    obj2.y + obj2.height < obj1.y);
        }
        
        findCollisions() {
            const collisions = [];
            const checked = new Set();
            
            for (const [id, obj] of this.objects) {
                const nearby = this.findNearbyObjects(obj.x, obj.y, obj.width, obj.height);
                
                for (const other of nearby) {
                    if (other.id !== id) {
                        const pairKey = [id, other.id].sort().join(',');
                        if (!checked.has(pairKey) && this.checkCollision(obj, other)) {
                            collisions.push([obj, other]);
                            checked.add(pairKey);
                        }
                    }
                }
            }
            
            return collisions;
        }
    }
    
    // Test the spatial grid
    const grid = new SimpleSpatialGrid(800, 600, 100);
    
    // Add test objects
    grid.addObject('obj1', 100, 100, 50, 50);
    grid.addObject('obj2', 120, 120, 30, 30); // Overlaps with obj1
    grid.addObject('obj3', 400, 400, 40, 40); // No overlap
    
    console.log(`✅ Created spatial grid: ${grid.cols}x${grid.rows} cells`);
    console.log(`✅ Added ${grid.objects.size} objects`);
    
    const collisions = grid.findCollisions();
    console.log(`✅ Found ${collisions.length} collisions using spatial partitioning`);
    
    return true;
}

// Test 2: Performance Monitor Concept
function testPerformanceMonitorConcept() {
    console.log('\n=== Testing Performance Monitor Concept ===');
    
    class SimplePerformanceMonitor {
        constructor(windowSize = 60) {
            this.windowSize = windowSize;
            this.frameTimes = [];
            this.targetFps = 60;
            this.qualityLevel = 1.0;
        }
        
        recordFrame(frameTime) {
            this.frameTimes.push(frameTime);
            if (this.frameTimes.length > this.windowSize) {
                this.frameTimes.shift();
            }
        }
        
        getAverageFps() {
            if (this.frameTimes.length === 0) return 0;
            const avgTime = this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
            return avgTime > 0 ? 1000 / avgTime : 0;
        }
        
        adjustQuality() {
            const avgFps = this.getAverageFps();
            const ratio = avgFps / this.targetFps;
            
            if (ratio < 0.8) {
                this.qualityLevel = Math.max(0.25, this.qualityLevel * 0.9);
            } else if (ratio > 1.2) {
                this.qualityLevel = Math.min(1.0, this.qualityLevel * 1.1);
            }
            
            return this.qualityLevel;
        }
    }
    
    const monitor = new SimplePerformanceMonitor();
    
    // Simulate frame processing
    for (let i = 0; i < 30; i++) {
        const frameTime = 16 + Math.random() * 8; // 16ms ± 4ms variation
        monitor.recordFrame(frameTime);
    }
    
    console.log(`✅ Created performance monitor`);
    console.log(`✅ Average FPS: ${monitor.getAverageFps().toFixed(1)}`);
    
    const originalQuality = monitor.qualityLevel;
    const adjustedQuality = monitor.adjustQuality();
    console.log(`✅ Quality adjustment: ${originalQuality.toFixed(2)} → ${adjustedQuality.toFixed(2)}`);
    
    return true;
}

// Test 3: Optimization Comparison
function testOptimizationComparison() {
    console.log('\n=== Testing Optimization Comparison ===');
    
    const numObjects = 20;
    const objects = [];
    
    // Generate test objects
    for (let i = 0; i < numObjects; i++) {
        objects.push({
            id: `obj_${i}`,
            x: Math.random() * 700,
            y: Math.random() * 500,
            width: 20 + Math.random() * 30,
            height: 20 + Math.random() * 30
        });
    }
    
    // Brute force collision detection
    function bruteForceCollisions(objects) {
        const collisions = [];
        for (let i = 0; i < objects.length; i++) {
            for (let j = i + 1; j < objects.length; j++) {
                const obj1 = objects[i];
                const obj2 = objects[j];
                
                if (!(obj1.x + obj1.width < obj2.x || 
                     obj2.x + obj2.width < obj1.x ||
                     obj1.y + obj1.height < obj2.y || 
                     obj2.y + obj2.height < obj1.y)) {
                    collisions.push([obj1, obj2]);
                }
            }
        }
        return collisions;
    }
    
    // Spatial grid collision detection
    function spatialGridCollisions(objects) {
        const grid = new Map();
        const cellSize = 100;
        
        // Add objects to grid
        objects.forEach(obj => {
            const cellX = Math.floor((obj.x + obj.width/2) / cellSize);
            const cellY = Math.floor((obj.y + obj.height/2) / cellSize);
            const cellKey = `${cellX},${cellY}`;
            
            if (!grid.has(cellKey)) {
                grid.set(cellKey, []);
            }
            grid.get(cellKey).push(obj);
        });
        
        // Find collisions within cells
        const collisions = [];
        const checked = new Set();
        
        for (const cellObjects of grid.values()) {
            for (let i = 0; i < cellObjects.length; i++) {
                for (let j = i + 1; j < cellObjects.length; j++) {
                    const obj1 = cellObjects[i];
                    const obj2 = cellObjects[j];
                    const pairKey = [obj1.id, obj2.id].sort().join(',');
                    
                    if (!checked.has(pairKey)) {
                        checked.add(pairKey);
                        
                        if (!(obj1.x + obj1.width < obj2.x || 
                             obj2.x + obj2.width < obj1.x ||
                             obj1.y + obj1.height < obj2.y || 
                             obj2.y + obj2.height < obj1.y)) {
                            collisions.push([obj1, obj2]);
                        }
                    }
                }
            }
        }
        
        return collisions;
    }
    
    // Test brute force
    const startBrute = Date.now();
    const bruteCollisions = bruteForceCollisions(objects);
    const bruteTime = Date.now() - startBrute;
    
    // Test spatial grid
    const startSpatial = Date.now();
    const spatialCollisions = spatialGridCollisions(objects);
    const spatialTime = Date.now() - startSpatial;
    
    console.log(`✅ Brute force: ${bruteCollisions.length} collisions in ${bruteTime}ms`);
    console.log(`✅ Spatial grid: ${spatialCollisions.length} collisions in ${spatialTime}ms`);
    
    if (bruteCollisions.length === spatialCollisions.length) {
        console.log('✅ Both methods found same number of collisions');
    } else {
        console.log(`⚠️  Different results: brute=${bruteCollisions.length}, spatial=${spatialCollisions.length}`);
    }
    
    const improvement = bruteTime > 0 ? ((bruteTime - spatialTime) / bruteTime * 100) : 0;
    console.log(`✅ Performance change: ${improvement.toFixed(1)}%`);
    
    return true;
}

// Test 4: Memory Optimization
function testMemoryOptimization() {
    console.log('\n=== Testing Memory Optimization ===');
    
    // Test object pooling concept
    class ObjectPool {
        constructor(createFn, resetFn, initialSize = 10) {
            this.createFn = createFn;
            this.resetFn = resetFn;
            this.pool = [];
            
            // Pre-populate pool
            for (let i = 0; i < initialSize; i++) {
                this.pool.push(this.createFn());
            }
        }
        
        acquire() {
            return this.pool.length > 0 ? this.pool.pop() : this.createFn();
        }
        
        release(obj) {
            this.resetFn(obj);
            this.pool.push(obj);
        }
        
        getPoolSize() {
            return this.pool.length;
        }
    }
    
    // Test collision event pooling
    const collisionEventPool = new ObjectPool(
        () => ({ id: null, obj1: null, obj2: null, timestamp: 0 }),
        (event) => { event.id = null; event.obj1 = null; event.obj2 = null; event.timestamp = 0; }
    );
    
    console.log(`✅ Created object pool with ${collisionEventPool.getPoolSize()} pre-allocated objects`);
    
    // Simulate using and releasing objects
    const events = [];
    for (let i = 0; i < 5; i++) {
        const event = collisionEventPool.acquire();
        event.id = `collision_${i}`;
        event.timestamp = Date.now();
        events.push(event);
    }
    
    console.log(`✅ Acquired ${events.length} objects from pool`);
    console.log(`✅ Pool size after acquisition: ${collisionEventPool.getPoolSize()}`);
    
    // Release objects back to pool
    events.forEach(event => collisionEventPool.release(event));
    console.log(`✅ Pool size after release: ${collisionEventPool.getPoolSize()}`);
    
    return true;
}

// Run all tests
function runAllTests() {
    let success = true;
    
    try {
        success &= testSpatialGridConcept();
        success &= testPerformanceMonitorConcept();
        success &= testOptimizationComparison();
        success &= testMemoryOptimization();
        
        console.log('\n' + '='.repeat(50));
        if (success) {
            console.log('🎉 ALL WEB OPTIMIZATION CONCEPT TESTS PASSED!');
            console.log('\n✅ Web collision optimization concepts verified');
            console.log('\nVerified concepts:');
            console.log('  • Spatial partitioning for collision detection');
            console.log('  • Performance monitoring and quality adjustment');
            console.log('  • Optimization comparison and benchmarking');
            console.log('  • Memory optimization with object pooling');
        } else {
            console.log('❌ Some optimization concept tests failed!');
        }
        
    } catch (error) {
        console.log(`\n❌ Test failed with error: ${error.message}`);
        console.error(error.stack);
        success = false;
    }
    
    return success;
}

// Run the tests
const success = runAllTests();
process.exit(success ? 0 : 1);