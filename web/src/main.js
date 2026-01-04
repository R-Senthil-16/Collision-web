// Main application entry point
console.log('Collision Detection System - Web Application Starting...');

// Global collision system instance
let collisionSystem = null;

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Video analysis and hardware control interface initialized');
    
    // Initialize collision system for simulation
    initializeCollisionSystem();
    
    // Initialize tab management
    initializeTabs();
    
    // Initialize video upload functionality
    initializeVideoUpload();
    
    // Initialize live feed functionality
    initializeLiveFeed();
    
    // Initialize hardware control
    initializeHardwareControl();
    
    // Initialize performance monitoring
    initializePerformanceMonitoring();
});

function initializeCollisionSystem() {
    // Get canvas dimensions (assuming a canvas exists or will be created)
    const canvasWidth = 800;
    const canvasHeight = 600;
    
    // Create optimized collision system
    if (typeof window.CollisionSystem !== 'undefined') {
        collisionSystem = new window.CollisionSystem.OptimizedCollisionSystem(canvasWidth, canvasHeight);
        
        // Set up collision event handling
        collisionSystem.onCollision((collision) => {
            console.log('Collision detected:', collision);
            // Could trigger visual effects, sounds, or other responses
        });
        
        // Enable adaptive quality by default
        collisionSystem.enableAdaptiveQuality(true);
        collisionSystem.setPerformanceTarget(60); // Target 60 FPS
        
        console.log('Optimized collision system initialized');
    } else {
        console.warn('CollisionSystem not available, falling back to basic collision detection');
    }
}

function initializePerformanceMonitoring() {
    if (!collisionSystem) {
        return;
    }
    
    // Create performance display element
    const performanceDisplay = document.createElement('div');
    performanceDisplay.id = 'performance-display';
    performanceDisplay.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-family: monospace;
        font-size: 12px;
        z-index: 1000;
        min-width: 200px;
        display: none;
    `;
    document.body.appendChild(performanceDisplay);
    
    // Add toggle button for performance display
    const toggleButton = document.createElement('button');
    toggleButton.textContent = 'Performance';
    toggleButton.style.cssText = `
        position: fixed;
        top: 10px;
        right: 220px;
        z-index: 1001;
        padding: 5px 10px;
        background: #007bff;
        color: white;
        border: none;
        border-radius: 3px;
        cursor: pointer;
    `;
    
    let performanceVisible = false;
    toggleButton.addEventListener('click', () => {
        performanceVisible = !performanceVisible;
        performanceDisplay.style.display = performanceVisible ? 'block' : 'none';
        toggleButton.textContent = performanceVisible ? 'Hide Perf' : 'Performance';
    });
    
    document.body.appendChild(toggleButton);
    
    // Update performance display periodically
    setInterval(() => {
        if (performanceVisible && collisionSystem) {
            const summary = collisionSystem.getPerformanceSummary();
            
            performanceDisplay.innerHTML = `
                <div><strong>Performance Monitor</strong></div>
                <div>FPS: ${summary.performanceMetrics.averageFps.toFixed(1)}</div>
                <div>Frame Time: ${summary.performanceMetrics.averageFrameTime.toFixed(2)}ms</div>
                <div>Objects: ${summary.performanceMetrics.averageObjects.toFixed(0)}</div>
                <div>Collisions/Frame: ${summary.frameProcessing.collisionsPerFrame.toFixed(2)}</div>
                <div>Quality: ${(summary.qualitySettings.currentQualityLevel * 100).toFixed(0)}%</div>
                <div>Spatial Opt: ${summary.spatialOptimization.enabled ? 'ON' : 'OFF'}</div>
                ${summary.spatialOptimization.enabled ? 
                    `<div>Grid Cells: ${summary.spatialOptimization.stats.activeCells}/${summary.spatialOptimization.stats.totalCells}</div>
                     <div>Cell Util: ${(summary.spatialOptimization.stats.cellUtilization * 100).toFixed(1)}%</div>` : ''
                }
                <div>Total Frames: ${summary.frameProcessing.totalFramesProcessed}</div>
                <div>Total Collisions: ${summary.frameProcessing.totalCollisionsDetected}</div>
            `;
        }
    }, 1000); // Update every second
}

function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const panels = document.querySelectorAll('.panel');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all tabs and panels
            tabButtons.forEach(btn => btn.classList.remove('active'));
            panels.forEach(panel => panel.classList.remove('active'));
            
            // Add active class to clicked tab
            button.classList.add('active');
            
            // Show corresponding panel
            const panelId = button.id.replace('-tab', '-panel');
            const panel = document.getElementById(panelId);
            if (panel) {
                panel.classList.add('active');
            }
        });
    });
}

function initializeVideoUpload() {
    const videoUpload = document.getElementById('video-upload');
    const progressBar = document.getElementById('upload-progress-fill');
    const analysisVideo = document.getElementById('analysis-video');
    const resultsDiv = document.getElementById('analysis-results');
    
    if (videoUpload) {
        videoUpload.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                console.log('Video file selected:', file.name);
                // TODO: Implement video upload and processing
                resultsDiv.innerHTML = '<p>Video processing functionality will be implemented in future tasks.</p>';
            }
        });
    }
}

function initializeLiveFeed() {
    // LiveFeedViewer is now initialized automatically via its own DOMContentLoaded listener
    // Set up any additional integration here if needed
    
    // Set up callbacks for live feed events
    if (typeof liveFeedViewer !== 'undefined' && liveFeedViewer) {
        liveFeedViewer.setCallbacks({
            onCameraConnected: (cameraId) => {
                console.log(`Camera ${cameraId} connected successfully`);
            },
            onCameraDisconnected: (cameraId) => {
                console.log(`Camera ${cameraId} disconnected`);
            },
            onCollisionDetected: (alert) => {
                console.log('Collision detected:', alert);
                // Could trigger additional UI updates here
            },
            onError: (message) => {
                console.error('Live feed error:', message);
                // Could show error notifications here
            }
        });
    }
}

function initializeHardwareControl() {
    // Hardware interface is now initialized automatically via its own DOMContentLoaded listener
    // Set up any additional integration here if needed
    
    // Add connection status indicator to the hardware panel
    const hardwarePanel = document.getElementById('hardware-panel');
    if (hardwarePanel && !document.getElementById('hardware-connection-status')) {
        const deviceList = hardwarePanel.querySelector('.device-list h3');
        if (deviceList) {
            const statusIndicator = document.createElement('span');
            statusIndicator.id = 'hardware-connection-status';
            statusIndicator.className = 'status-disconnected';
            statusIndicator.textContent = 'Disconnected';
            deviceList.appendChild(statusIndicator);
        }
    }
    
    // Set up callbacks for hardware events
    if (typeof hardwareInterface !== 'undefined' && hardwareInterface) {
        hardwareInterface.setCallbacks({
            onDeviceUpdate: (device) => {
                console.log(`Device ${device.device_id} updated:`, device);
            },
            onCommandResponse: (response) => {
                console.log('Command response:', response);
            },
            onError: (message) => {
                console.error('Hardware error:', message);
            }
        });
    }
}