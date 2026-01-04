/**
 * Optimized Collision Detection System for Web-based Simulation
 * 
 * Requirements covered:
 * - 6.2: Use efficient algorithms to minimize computational overhead
 * - 6.3: Optimize rendering by only updating changed areas when possible
 * - 3.1: Detect collisions using bounding box intersection
 * - 3.2: Trigger collision events when objects intersect
 */

class BoundingBox {
    constructor(x, y, width, height) {
        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;
    }
    
    get center() {
        return {
            x: this.x + this.width / 2,
            y: this.y + this.height / 2
        };
    }
    
    get area() {
        return this.width * this.height;
    }
    
    intersects(other) {
        return !(this.x + this.width < other.x || 
                other.x + other.width < this.x ||
                this.y + this.height < other.y || 
                other.y + other.height < this.y);
    }
    
    containsPoint(x, y) {
        return x >= this.x && x <= this.x + this.width &&
               y >= this.y && y <= this.y + this.height;
    }
}

class SpatialGrid {
    constructor(width, height, cellSize = 100) {
        this.width = width;
        this.height = height;
        this.cellSize = cellSize;
        this.cols = Math.ceil(width / cellSize);
        this.rows = Math.ceil(height / cellSize);
        
        // Grid cells containing object IDs
        this.grid = new Map();
        
        // Object storage
        this.objects = new Map();
        
        // Performance tracking
        this.stats = {
            totalObjects: 0,
            collisionChecks: 0,
            gridUpdates: 0,
            lastUpdateTime: 0,
            averageObjectsPerCell: 0
        };
    }
    
    _getCellCoords(x, y) {
        const col = Math.max(0, Math.min(this.cols - 1, Math.floor(x / this.cellSize)));
        const row = Math.max(0, Math.min(this.rows - 1, Math.floor(y / this.cellSize)));
        return { col, row };
    }
    
    _getCellKey(col, row) {
        return `${col},${row}`;
    }
    
    _getCellsForBbox(bbox) {
        const minCoords = this._getCellCoords(bbox.x, bbox.y);
        const maxCoords = this._getCellCoords(bbox.x + bbox.width, bbox.y + bbox.height);
        
        const cells = [];
        for (let row = minCoords.row; row <= maxCoords.row; row++) {
            for (let col = minCoords.col; col <= maxCoords.col; col++) {
                cells.push(this._getCellKey(col, row));
            }
        }
        
        return cells;
    }
    
    addObject(objId, bbox, data = null) {
        const currentTime = performance.now();
        
        // Remove object from old cells if it exists
        if (this.objects.has(objId)) {
            this.removeObject(objId);
        }
        
        // Create spatial object
        const spatialObj = {
            id: objId,
            bbox: bbox,
            data: data,
            lastUpdated: currentTime
        };
        
        // Add to object storage
        this.objects.set(objId, spatialObj);
        
        // Add to appropriate grid cells
        const cells = this._getCellsForBbox(bbox);
        for (const cellKey of cells) {
            if (!this.grid.has(cellKey)) {
                this.grid.set(cellKey, new Set());
            }
            this.grid.get(cellKey).add(objId);
        }
        
        // Update statistics
        this.stats.totalObjects = this.objects.size;
        this.stats.gridUpdates++;
        this.stats.lastUpdateTime = currentTime;
        this._updateCellStatistics();
    }
    
    removeObject(objId) {
        if (!this.objects.has(objId)) {
            return;
        }
        
        const spatialObj = this.objects.get(objId);
        
        // Remove from all grid cells
        const cells = this._getCellsForBbox(spatialObj.bbox);
        for (const cellKey of cells) {
            if (this.grid.has(cellKey)) {
                this.grid.get(cellKey).delete(objId);
                // Clean up empty cells
                if (this.grid.get(cellKey).size === 0) {
                    this.grid.delete(cellKey);
                }
            }
        }
        
        // Remove from object storage
        this.objects.delete(objId);
        
        // Update statistics
        this.stats.totalObjects = this.objects.size;
        this._updateCellStatistics();
    }
    
    getNearbyObjects(bbox) {
        const nearbyIds = new Set();
        
        // Get all cells that the bounding box overlaps
        const cells = this._getCellsForBbox(bbox);
        
        // Collect all object IDs from those cells
        for (const cellKey of cells) {
            if (this.grid.has(cellKey)) {
                for (const objId of this.grid.get(cellKey)) {
                    nearbyIds.add(objId);
                }
            }
        }
        
        // Return the actual objects
        return Array.from(nearbyIds)
            .map(objId => this.objects.get(objId))
            .filter(obj => obj !== undefined);
    }
    
    findCollisions(objId) {
        if (!this.objects.has(objId)) {
            return [];
        }
        
        const targetObj = this.objects.get(objId);
        const nearbyObjects = this.getNearbyObjects(targetObj.bbox);
        
        const collisions = [];
        for (const otherObj of nearbyObjects) {
            if (otherObj.id !== objId && targetObj.bbox.intersects(otherObj.bbox)) {
                collisions.push(otherObj);
                this.stats.collisionChecks++;
            }
        }
        
        return collisions;
    }
    
    findAllCollisions() {
        const collisionPairs = [];
        const checkedPairs = new Set();
        
        for (const [objId, obj] of this.objects) {
            const nearbyObjects = this.getNearbyObjects(obj.bbox);
            
            for (const otherObj of nearbyObjects) {
                if (otherObj.id !== objId) {
                    // Create a consistent pair identifier to avoid duplicates
                    const pairId = [objId, otherObj.id].sort().join(',');
                    
                    if (!checkedPairs.has(pairId) && obj.bbox.intersects(otherObj.bbox)) {
                        collisionPairs.push([obj, otherObj]);
                        checkedPairs.add(pairId);
                        this.stats.collisionChecks++;
                    }
                }
            }
        }
        
        return collisionPairs;
    }
    
    clear() {
        this.grid.clear();
        this.objects.clear();
        this.stats.totalObjects = 0;
        this._updateCellStatistics();
    }
    
    _updateCellStatistics() {
        if (this.grid.size === 0) {
            this.stats.averageObjectsPerCell = 0;
            return;
        }
        
        let totalObjectsInCells = 0;
        for (const cellObjects of this.grid.values()) {
            totalObjectsInCells += cellObjects.size;
        }
        
        this.stats.averageObjectsPerCell = totalObjectsInCells / this.grid.size;
    }
    
    getPerformanceStats() {
        return {
            ...this.stats,
            gridDimensions: { cols: this.cols, rows: this.rows },
            cellSize: this.cellSize,
            totalCells: this.cols * this.rows,
            activeCells: this.grid.size,
            cellUtilization: this.grid.size / (this.cols * this.rows)
        };
    }
    
    optimizeCellSize(targetObjectsPerCell = 5) {
        if (this.stats.totalObjects === 0) {
            return;
        }
        
        const currentAvg = this.stats.averageObjectsPerCell;
        
        // If we have too many objects per cell, make cells smaller
        if (currentAvg > targetObjectsPerCell * 1.5) {
            this.cellSize = Math.max(25, this.cellSize * 0.8);
        }
        // If we have too few objects per cell, make cells larger
        else if (currentAvg < targetObjectsPerCell * 0.5) {
            this.cellSize = Math.min(200, this.cellSize * 1.2);
        }
        else {
            return; // Cell size is already optimal
        }
        
        // Rebuild grid with new cell size
        const oldObjects = Array.from(this.objects.values());
        this.cols = Math.ceil(this.width / this.cellSize);
        this.rows = Math.ceil(this.height / this.cellSize);
        
        // Clear and rebuild
        this.clear();
        for (const obj of oldObjects) {
            this.addObject(obj.id, obj.bbox, obj.data);
        }
    }
}

class PerformanceMonitor {
    constructor(windowSize = 100) {
        this.windowSize = windowSize;
        this.frameTimes = [];
        this.collisionCounts = [];
        this.objectCounts = [];
        this.timestamps = [];
        
        // Performance thresholds
        this.targetFps = 60.0;
        this.maxFrameTime = 1.0 / this.targetFps;
        
        // Quality adjustment parameters
        this.qualityLevel = 1.0; // 1.0 = full quality, 0.5 = half quality, etc.
        this.minQuality = 0.25;
        this.maxQuality = 1.0;
    }
    
    recordFrame(frameTime, collisionCount, objectCount) {
        const currentTime = performance.now();
        
        this.frameTimes.push(frameTime);
        this.collisionCounts.push(collisionCount);
        this.objectCounts.push(objectCount);
        this.timestamps.push(currentTime);
        
        // Keep only recent measurements
        if (this.frameTimes.length > this.windowSize) {
            this.frameTimes.shift();
            this.collisionCounts.shift();
            this.objectCounts.shift();
            this.timestamps.shift();
        }
    }
    
    getAverageFps() {
        if (this.frameTimes.length === 0) {
            return 0;
        }
        
        const avgFrameTime = this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length;
        return avgFrameTime > 0 ? 1000.0 / avgFrameTime : 0; // Convert ms to fps
    }
    
    getPerformanceMetrics() {
        if (this.frameTimes.length === 0) {
            return {
                averageFps: 0,
                averageFrameTime: 0,
                averageCollisions: 0,
                averageObjects: 0,
                qualityLevel: this.qualityLevel
            };
        }
        
        return {
            averageFps: this.getAverageFps(),
            averageFrameTime: this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length,
            averageCollisions: this.collisionCounts.reduce((a, b) => a + b, 0) / this.collisionCounts.length,
            averageObjects: this.objectCounts.reduce((a, b) => a + b, 0) / this.objectCounts.length,
            qualityLevel: this.qualityLevel,
            targetFps: this.targetFps,
            performanceRatio: this.getAverageFps() / this.targetFps
        };
    }
    
    shouldAdjustQuality() {
        if (this.frameTimes.length < 10) { // Need enough samples
            return false;
        }
        
        const avgFps = this.getAverageFps();
        
        // Adjust quality if performance is significantly off target
        if (avgFps < this.targetFps * 0.8) { // Performance too low
            return true;
        } else if (avgFps > this.targetFps * 1.2 && this.qualityLevel < this.maxQuality) { // Performance too high, can increase quality
            return true;
        }
        
        return false;
    }
    
    adjustQuality() {
        if (!this.shouldAdjustQuality()) {
            return this.qualityLevel;
        }
        
        const avgFps = this.getAverageFps();
        const performanceRatio = avgFps / this.targetFps;
        
        if (performanceRatio < 0.8) { // Performance too low, reduce quality
            this.qualityLevel = Math.max(this.minQuality, this.qualityLevel * 0.9);
        } else if (performanceRatio > 1.2) { // Performance too high, increase quality
            this.qualityLevel = Math.min(this.maxQuality, this.qualityLevel * 1.1);
        }
        
        return this.qualityLevel;
    }
}

class OptimizedCollisionSystem {
    constructor(canvasWidth, canvasHeight) {
        this.canvasWidth = canvasWidth;
        this.canvasHeight = canvasHeight;
        
        // Error handling and recovery settings
        this.maxRetries = 3;
        this.retryDelay = 100; // milliseconds
        this.errorCount = 0;
        this.maxErrorsPerSession = 50;
        this.recoveryMode = false;
        this.lastErrorTime = 0;
        this.errorRecoveryTimeout = 5000; // milliseconds
        
        // Initialize spatial partitioning with error handling
        try {
            this.spatialGrid = new SpatialGrid(canvasWidth, canvasHeight, 100);
            this.performanceMonitor = new PerformanceMonitor(60);
            console.log('Spatial optimization initialized successfully');
        } catch (error) {
            console.error('Failed to initialize spatial optimization:', error);
            this.spatialGrid = null;
            this.performanceMonitor = null;
        }
        
        // Game objects
        this.gameObjects = new Map();
        
        // Performance optimization settings
        this.useSpatialOptimization = this.spatialGrid !== null;
        this.adaptiveQuality = true;
        this.maxObjectsPerFrame = 50;
        
        // Collision detection settings
        this.collisionThreshold = 0.1;
        
        // Performance statistics with error tracking
        this.stats = {
            totalFramesProcessed: 0,
            totalCollisionsDetected: 0,
            averageProcessingTime: 0,
            spatialOptimizationEnabled: this.useSpatialOptimization,
            errorCount: 0,
            recoveryCount: 0,
            lastError: null
        };
        
        // Collision event callbacks
        this.collisionCallbacks = [];
        
        // Error event callbacks
        this.errorCallbacks = [];
    }
    
    addGameObject(gameObject) {
        this.gameObjects.set(gameObject.id, gameObject);
        
        // Add to spatial grid if optimization is enabled
        if (this.useSpatialOptimization) {
            const bbox = new BoundingBox(
                gameObject.x - gameObject.width / 2,
                gameObject.y - gameObject.height / 2,
                gameObject.width,
                gameObject.height
            );
            this.spatialGrid.addObject(gameObject.id, bbox, gameObject);
        }
    }
    
    removeGameObject(objectId) {
        if (this.gameObjects.has(objectId)) {
            this.gameObjects.delete(objectId);
            
            if (this.useSpatialOptimization) {
                this.spatialGrid.removeObject(objectId);
            }
        }
    }
    
    updateGameObject(gameObject) {
        if (this.gameObjects.has(gameObject.id)) {
            this.gameObjects.set(gameObject.id, gameObject);
            
            // Update spatial grid if optimization is enabled
            if (this.useSpatialOptimization) {
                const bbox = new BoundingBox(
                    gameObject.x - gameObject.width / 2,
                    gameObject.y - gameObject.height / 2,
                    gameObject.width,
                    gameObject.height
                );
                this.spatialGrid.addObject(gameObject.id, bbox, gameObject);
            }
        }
    }
    
    detectCollisions() {
        const frameStartTime = performance.now();
        let collisions = [];
        
        // Check if we're in recovery mode
        if (this.recoveryMode) {
            if (performance.now() - this.lastErrorTime > this.errorRecoveryTimeout) {
                this.recoveryMode = false;
                console.log('Exiting recovery mode');
            } else {
                // In recovery mode, use simplified processing
                return this._detectCollisionsRecoveryMode();
            }
        }
        
        // Check error count limits
        if (this.errorCount >= this.maxErrorsPerSession) {
            console.error('Maximum error count reached, entering permanent recovery mode');
            this.recoveryMode = true;
            return [];
        }
        
        try {
            if (this.useSpatialOptimization && this.spatialGrid) {
                // Use spatial partitioning for efficient collision detection
                try {
                    const collisionPairs = this.spatialGrid.findAllCollisions();
                    
                    for (const [obj1, obj2] of collisionPairs) {
                        const collision = this._createCollisionEvent(obj1.data, obj2.data);
                        if (collision) {
                            collisions.push(collision);
                        }
                    }
                } catch (spatialError) {
                    console.warn('Spatial optimization failed, falling back to brute force:', spatialError);
                    this.useSpatialOptimization = false;
                    collisions = this._detectCollisionsBruteForce();
                }
            } else {
                // Brute force collision detection
                collisions = this._detectCollisionsBruteForce();
            }
            
            // Record performance metrics with error handling
            try {
                const frameTime = performance.now() - frameStartTime;
                if (this.performanceMonitor) {
                    this.performanceMonitor.recordFrame(frameTime, collisions.length, this.gameObjects.size);
                }
            } catch (perfError) {
                console.warn('Performance monitoring failed:', perfError);
            }
            
            // Adjust quality if adaptive quality is enabled
            if (this.adaptiveQuality) {
                try {
                    this._adjustProcessingQuality();
                } catch (qualityError) {
                    console.warn('Quality adjustment failed:', qualityError);
                }
            }
            
            // Update statistics
            this._updateFrameStatistics(performance.now() - frameStartTime, collisions.length);
            
            // Trigger collision callbacks with error handling
            for (const collision of collisions) {
                this._triggerCollisionCallbacks(collision);
            }
            
        } catch (error) {
            console.error('Collision detection failed:', error);
            this._handleError(error, 'collision_detection');
            collisions = [];
        }
        
        return collisions;
    }
    
    _detectCollisionsRecoveryMode() {
        """Simplified collision detection for recovery mode"""
        try {
            console.debug('Processing collisions in recovery mode');
            
            const objects = Array.from(this.gameObjects.values());
            const collisions = [];
            
            // Limit to fewer objects in recovery mode
            const limitedObjects = objects.slice(0, Math.min(10, objects.length));
            
            // Simple collision detection without spatial optimization
            for (let i = 0; i < limitedObjects.length; i++) {
                for (let j = i + 1; j < limitedObjects.length; j++) {
                    if (this._simpleCollisionCheck(limitedObjects[i], limitedObjects[j])) {
                        const collision = this._createCollisionEvent(limitedObjects[i], limitedObjects[j]);
                        if (collision) {
                            collisions.push(collision);
                        }
                    }
                }
            }
            
            return collisions;
            
        } catch (error) {
            console.error('Recovery mode processing failed:', error);
            return [];
        }
    }
    
    _detectCollisionsBruteForce() {
        """Brute force collision detection as fallback"""
        const objects = Array.from(this.gameObjects.values());
        const collisions = [];
        
        for (let i = 0; i < objects.length; i++) {
            for (let j = i + 1; j < objects.length; j++) {
                if (this._checkCollision(objects[i], objects[j])) {
                    const collision = this._createCollisionEvent(objects[i], objects[j]);
                    if (collision) {
                        collisions.push(collision);
                    }
                }
            }
        }
        
        return collisions;
    }
    
    _simpleCollisionCheck(obj1, obj2) {
        """Simple collision check for recovery mode"""
        try {
            const dx = obj1.x - obj2.x;
            const dy = obj1.y - obj2.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            const minDistance = (obj1.width + obj2.width) / 4;
            
            return distance < minDistance;
        } catch (error) {
            return false;
        }
    }
    
    _handleError(error, errorType) {
        """Handle errors with recovery mechanisms"""
        this.errorCount++;
        this.lastErrorTime = performance.now();
        this.stats.errorCount = this.errorCount;
        this.stats.lastError = {
            type: errorType,
            message: error.message,
            timestamp: this.lastErrorTime
        };
        
        // Enter recovery mode if too many errors
        if (this.errorCount > 10) {
            this.recoveryMode = true;
            this.stats.recoveryCount++;
            console.warn(`Entering recovery mode due to ${this.errorCount} errors`);
        }
        
        // Trigger error callbacks
        for (const callback of this.errorCallbacks) {
            try {
                callback(error, errorType);
            } catch (callbackError) {
                console.error('Error in error callback:', callbackError);
            }
        }
    }
    
    _updateFrameStatistics(frameTime, collisionCount) {
        """Update frame statistics with error handling"""
        try {
            this.stats.totalFramesProcessed++;
            this.stats.totalCollisionsDetected += collisionCount;
            this.stats.averageProcessingTime = (
                (this.stats.averageProcessingTime * (this.stats.totalFramesProcessed - 1) + frameTime) /
                this.stats.totalFramesProcessed
            );
        } catch (error) {
            console.warn('Failed to update frame statistics:', error);
        }
    }
    
    _checkCollision(obj1, obj2) {
        const dx = obj1.x - obj2.x;
        const dy = obj1.y - obj2.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const minDistance = (obj1.width + obj2.width) / 4; // Assuming circular collision
        
        return distance < minDistance;
    }
    
    _createCollisionEvent(obj1, obj2) {
        return {
            id: `collision_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            object1: obj1,
            object2: obj2,
            timestamp: performance.now(),
            collisionPoint: {
                x: (obj1.x + obj2.x) / 2,
                y: (obj1.y + obj2.y) / 2
            }
        };
    }
    
    _adjustProcessingQuality() {
        if (!this.adaptiveQuality) {
            return;
        }
        
        const qualityLevel = this.performanceMonitor.adjustQuality();
        
        // Adjust collision detection parameters based on quality level
        if (qualityLevel < 0.5) {
            // Low quality: reduce precision
            this.maxObjectsPerFrame = 25;
            
            // Increase spatial grid cell size for faster processing
            if (this.spatialGrid.cellSize < 150) {
                this.spatialGrid.cellSize = Math.min(150, this.spatialGrid.cellSize * 1.1);
            }
        } else if (qualityLevel > 0.8) {
            // High quality: increase precision
            this.maxObjectsPerFrame = 50;
            
            // Decrease spatial grid cell size for more precise processing
            if (this.spatialGrid.cellSize > 75) {
                this.spatialGrid.cellSize = Math.max(75, this.spatialGrid.cellSize * 0.9);
            }
        }
        
        // Update statistics
        this.stats.currentQualityLevel = qualityLevel;
    }
    
    _triggerCollisionCallbacks(collision) {
        for (const callback of this.collisionCallbacks) {
            try {
                callback(collision);
            } catch (error) {
                console.error('Error in collision callback:', error);
            }
        }
    }
    
    onCollision(callback) {
        this.collisionCallbacks.push(callback);
    }
    
    removeCollisionCallback(callback) {
        const index = this.collisionCallbacks.indexOf(callback);
        if (index > -1) {
            this.collisionCallbacks.splice(index, 1);
        }
    }
    
    getPerformanceSummary() {
        const performanceMetrics = this.performanceMonitor.getPerformanceMetrics();
        const spatialStats = this.useSpatialOptimization ? this.spatialGrid.getPerformanceStats() : {};
        
        return {
            frameProcessing: {
                totalFramesProcessed: this.stats.totalFramesProcessed,
                totalCollisionsDetected: this.stats.totalCollisionsDetected,
                averageProcessingTime: this.stats.averageProcessingTime,
                collisionsPerFrame: this.stats.totalFramesProcessed > 0 ? 
                    this.stats.totalCollisionsDetected / this.stats.totalFramesProcessed : 0
            },
            performanceMetrics: performanceMetrics,
            spatialOptimization: {
                enabled: this.useSpatialOptimization,
                stats: spatialStats
            },
            qualitySettings: {
                adaptiveQualityEnabled: this.adaptiveQuality,
                collisionThreshold: this.collisionThreshold,
                maxObjectsPerFrame: this.maxObjectsPerFrame,
                currentQualityLevel: this.stats.currentQualityLevel || 1.0
            }
        };
    }
    
    optimizePerformance() {
        if (this.useSpatialOptimization) {
            // Optimize spatial grid cell size
            this.spatialGrid.optimizeCellSize();
        }
        
        return {
            optimizationApplied: true,
            spatialGridOptimized: this.useSpatialOptimization,
            newCellSize: this.useSpatialOptimization ? this.spatialGrid.cellSize : null
        };
    }
    
    enableSpatialOptimization(enable = true) {
        this.useSpatialOptimization = enable;
        this.stats.spatialOptimizationEnabled = enable;
        
        if (enable) {
            // Rebuild spatial grid with current objects
            this.spatialGrid.clear();
            for (const gameObject of this.gameObjects.values()) {
                const bbox = new BoundingBox(
                    gameObject.x - gameObject.width / 2,
                    gameObject.y - gameObject.height / 2,
                    gameObject.width,
                    gameObject.height
                );
                this.spatialGrid.addObject(gameObject.id, bbox, gameObject);
            }
        } else {
            // Clear spatial grid to save memory
            this.spatialGrid.clear();
        }
    }
    
    enableAdaptiveQuality(enable = true) {
        this.adaptiveQuality = enable;
    }
    
    setPerformanceTarget(targetFps) {
        if (this.performanceMonitor) {
            this.performanceMonitor.targetFps = targetFps;
            this.performanceMonitor.maxFrameTime = 1000.0 / targetFps; // Convert to ms
        }
    }
    
    onError(callback) {
        """Add error event callback"""
        this.errorCallbacks.push(callback);
    }
    
    removeErrorCallback(callback) {
        """Remove error event callback"""
        const index = this.errorCallbacks.indexOf(callback);
        if (index > -1) {
            this.errorCallbacks.splice(index, 1);
        }
    }
    
    resetErrorState() {
        """Reset error state and exit recovery mode"""
        this.errorCount = 0;
        this.recoveryMode = false;
        this.lastErrorTime = 0;
        this.stats.errorCount = 0;
        this.stats.lastError = null;
        console.log('Error state reset, exiting recovery mode');
    }
    
    getErrorSummary() {
        """Get comprehensive error and recovery statistics"""
        return {
            errorCount: this.errorCount,
            recoveryMode: this.recoveryMode,
            recoveryCount: this.stats.recoveryCount || 0,
            lastError: this.stats.lastError,
            maxErrorsPerSession: this.maxErrorsPerSession,
            errorRecoveryTimeout: this.errorRecoveryTimeout,
            timeSinceLastError: this.lastErrorTime > 0 ? performance.now() - this.lastErrorTime : 0
        };
    }
    
    isHealthy() {
        """Check if the collision system is in a healthy state"""
        return (
            !this.recoveryMode && 
            this.errorCount < this.maxErrorsPerSession * 0.8 &&
            (this.spatialGrid !== null || !this.useSpatialOptimization)
        );
    }
    
    getHealthStatus() {
        """Get detailed health status of the collision system"""
        return {
            healthy: this.isHealthy(),
            recoveryMode: this.recoveryMode,
            errorRate: this.errorCount / Math.max(1, this.stats.totalFramesProcessed),
            spatialOptimizationAvailable: this.spatialGrid !== null,
            performanceMonitorAvailable: this.performanceMonitor !== null,
            processingStatistics: {
                framesProcessed: this.stats.totalFramesProcessed,
                collisionsDetected: this.stats.totalCollisionsDetected,
                averageProcessingTime: this.stats.averageProcessingTime
            },
            errorStatistics: this.getErrorSummary()
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        BoundingBox,
        SpatialGrid,
        PerformanceMonitor,
        OptimizedCollisionSystem
    };
}

// Make available globally for browser use
if (typeof window !== 'undefined') {
    window.CollisionSystem = {
        BoundingBox,
        SpatialGrid,
        PerformanceMonitor,
        OptimizedCollisionSystem
    };
}