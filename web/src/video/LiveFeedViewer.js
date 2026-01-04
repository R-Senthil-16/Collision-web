/**
 * LiveFeedViewer - Handles real-time camera feed integration with WebSocket streaming
 */
class LiveFeedViewer {
    constructor(config = {}) {
        this.apiBaseUrl = config.apiBaseUrl || 'http://localhost:5000';
        this.socketUrl = config.socketUrl || 'http://localhost:5000';
        
        // DOM elements
        this.cameraSelectElement = null;
        this.connectButtonElement = null;
        this.liveVideoElement = null;
        this.liveOverlayElement = null;
        this.alertsElement = null;
        
        // WebSocket connection
        this.socket = null;
        this.isConnected = false;
        
        // Camera state
        this.currentCameraId = null;
        this.isStreaming = false;
        this.availableCameras = [];
        
        // Collision detection state
        this.collisionAlerts = [];
        this.maxAlerts = 50;
        
        // Callbacks
        this.onCameraConnected = null;
        this.onCameraDisconnected = null;
        this.onCollisionDetected = null;
        this.onError = null;
        
        this.init();
    }
    
    init() {
        // Get DOM elements
        this.cameraSelectElement = document.getElementById('camera-select');
        this.connectButtonElement = document.getElementById('connect-camera');
        this.liveVideoElement = document.getElementById('live-video');
        this.liveOverlayElement = document.getElementById('live-overlay');
        this.alertsElement = document.getElementById('live-alerts');
        
        // Set up event listeners
        if (this.connectButtonElement) {
            this.connectButtonElement.addEventListener('click', () => this.toggleCameraConnection());
        }
        
        if (this.cameraSelectElement) {
            this.cameraSelectElement.addEventListener('change', (e) => this.handleCameraSelection(e));
        }
        
        // Initialize WebSocket connection
        this.initializeWebSocket();
        
        // Load available cameras
        this.loadAvailableCameras();
    }
    
    initializeWebSocket() {
        try {
            // Import Socket.IO if available
            if (typeof io !== 'undefined') {
                this.socket = io(this.socketUrl);
                this.setupSocketEventHandlers();
            } else {
                // Fallback to native WebSocket
                this.initializeNativeWebSocket();
            }
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            this.showError('Failed to connect to server');
        }
    }
    
    initializeNativeWebSocket() {
        const wsUrl = this.socketUrl.replace('http', 'ws') + '/socket.io/?transport=websocket';
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            this.isConnected = true;
            console.log('WebSocket connected');
            this.updateConnectionStatus('Connected to server');
        };
        
        this.socket.onclose = () => {
            this.isConnected = false;
            console.log('WebSocket disconnected');
            this.updateConnectionStatus('Disconnected from server');
            
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.initializeWebSocket(), 3000);
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showError('WebSocket connection error');
        };
        
        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
    }
    
    setupSocketEventHandlers() {
        if (!this.socket) return;
        
        // Connection events
        this.socket.on('connect', () => {
            this.isConnected = true;
            console.log('Socket.IO connected');
            this.updateConnectionStatus('Connected to server');
        });
        
        this.socket.on('disconnect', () => {
            this.isConnected = false;
            console.log('Socket.IO disconnected');
            this.updateConnectionStatus('Disconnected from server');
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Socket.IO connection error:', error);
            this.showError('Failed to connect to server');
        });
        
        // Camera frame events
        this.socket.on('camera_frame', (data) => {
            this.handleCameraFrame(data);
        });
        
        // Collision detection events
        this.socket.on('collision_alert', (data) => {
            this.handleCollisionAlert(data);
        });
        
        // Camera stream events
        this.socket.on('camera_stream_started', (data) => {
            this.handleStreamStarted(data);
        });
        
        this.socket.on('camera_stream_stopped', (data) => {
            this.handleStreamStopped(data);
        });
        
        // Status and error events
        this.socket.on('status', (data) => {
            console.log('Status update:', data);
        });
        
        this.socket.on('error', (data) => {
            console.error('Server error:', data);
            this.showError(data.message || 'Server error occurred');
        });
    }
    
    handleSocketMessage(data) {
        switch (data.type) {
            case 'camera_frame':
                this.handleCameraFrame(data);
                break;
            case 'collision_alert':
                this.handleCollisionAlert(data);
                break;
            case 'camera_stream_started':
                this.handleStreamStarted(data);
                break;
            case 'camera_stream_stopped':
                this.handleStreamStopped(data);
                break;
            case 'error':
                this.showError(data.message || 'Server error occurred');
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }
    
    async loadAvailableCameras() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/cameras`);
            
            if (response.ok) {
                const data = await response.json();
                this.availableCameras = data.available_cameras || [];
                this.updateCameraSelect();
            } else {
                console.error('Failed to load available cameras');
                this.showError('Failed to load camera list');
            }
        } catch (error) {
            console.error('Error loading cameras:', error);
            this.showError('Failed to connect to camera service');
        }
    }
    
    updateCameraSelect() {
        if (!this.cameraSelectElement) return;
        
        // Clear existing options except the first one
        while (this.cameraSelectElement.children.length > 1) {
            this.cameraSelectElement.removeChild(this.cameraSelectElement.lastChild);
        }
        
        // Add available cameras
        this.availableCameras.forEach(cameraId => {
            const option = document.createElement('option');
            option.value = cameraId;
            option.textContent = `Camera ${cameraId}`;
            this.cameraSelectElement.appendChild(option);
        });
        
        // Update status
        if (this.availableCameras.length === 0) {
            this.updateConnectionStatus('No cameras detected');
        } else {
            this.updateConnectionStatus(`${this.availableCameras.length} camera(s) available`);
        }
    }
    
    handleCameraSelection(event) {
        const selectedCameraId = parseInt(event.target.value);
        
        if (isNaN(selectedCameraId)) {
            this.currentCameraId = null;
            return;
        }
        
        // If currently streaming from a different camera, switch
        if (this.isStreaming && this.currentCameraId !== selectedCameraId) {
            this.switchCamera(selectedCameraId);
        } else {
            this.currentCameraId = selectedCameraId;
        }
    }
    
    toggleCameraConnection() {
        if (this.isStreaming) {
            this.disconnectCamera();
        } else {
            this.connectCamera();
        }
    }
    
    async connectCamera() {
        if (!this.isConnected) {
            this.showError('Not connected to server');
            return;
        }
        
        if (this.currentCameraId === null) {
            this.showError('Please select a camera first');
            return;
        }
        
        try {
            this.updateConnectionStatus('Connecting to camera...');
            this.updateConnectButton('Connecting...', true);
            
            // Request camera stream start via WebSocket
            if (this.socket && this.socket.emit) {
                this.socket.emit('start_camera_stream', {
                    camera_id: this.currentCameraId
                });
            } else if (this.socket && this.socket.send) {
                this.socket.send(JSON.stringify({
                    type: 'start_camera_stream',
                    camera_id: this.currentCameraId
                }));
            }
            
            // Also make HTTP request to start camera feed
            const response = await fetch(`${this.apiBaseUrl}/api/camera/${this.currentCameraId}/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Camera start response:', result);
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to start camera');
            }
            
        } catch (error) {
            console.error('Error connecting to camera:', error);
            this.showError(`Failed to connect to camera: ${error.message}`);
            this.updateConnectButton('Connect', false);
        }
    }
    
    async disconnectCamera() {
        if (!this.currentCameraId) return;
        
        try {
            this.updateConnectionStatus('Disconnecting camera...');
            this.updateConnectButton('Disconnecting...', true);
            
            // Request camera stream stop via WebSocket
            if (this.socket && this.socket.emit) {
                this.socket.emit('stop_camera_stream', {
                    camera_id: this.currentCameraId
                });
            } else if (this.socket && this.socket.send) {
                this.socket.send(JSON.stringify({
                    type: 'stop_camera_stream',
                    camera_id: this.currentCameraId
                }));
            }
            
            // Also make HTTP request to stop camera feed
            const response = await fetch(`${this.apiBaseUrl}/api/camera/${this.currentCameraId}/stop`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Camera stop response:', result);
            }
            
        } catch (error) {
            console.error('Error disconnecting camera:', error);
            this.showError(`Failed to disconnect camera: ${error.message}`);
        }
    }
    
    async switchCamera(newCameraId) {
        if (this.currentCameraId === newCameraId) return;
        
        try {
            this.updateConnectionStatus('Switching camera...');
            
            // Stop current camera
            if (this.isStreaming) {
                await this.disconnectCamera();
            }
            
            // Start new camera
            this.currentCameraId = newCameraId;
            await this.connectCamera();
            
        } catch (error) {
            console.error('Error switching camera:', error);
            this.showError(`Failed to switch camera: ${error.message}`);
        }
    }
    
    handleCameraFrame(data) {
        if (data.camera_id !== this.currentCameraId) return;
        
        try {
            // Display frame in video element
            if (this.liveVideoElement && data.frame_data) {
                const imageUrl = `data:image/jpeg;base64,${data.frame_data}`;
                
                // Create or update video source
                if (!this.liveVideoElement.src || this.liveVideoElement.src !== imageUrl) {
                    this.liveVideoElement.src = imageUrl;
                }
            }
            
            // Handle collision overlay if present
            if (data.metadata && data.metadata.detections) {
                this.displayCollisionOverlay(data.metadata.detections);
            }
            
            // Update frame counter
            this.updateFrameInfo(data.metadata);
            
        } catch (error) {
            console.error('Error handling camera frame:', error);
        }
    }
    
    handleCollisionAlert(data) {
        try {
            console.log('Collision alert received:', data);
            
            // Add to alerts list
            const alert = {
                id: data.collision_id || `alert_${Date.now()}`,
                camera_id: data.camera_id,
                timestamp: new Date(data.timestamp),
                severity: data.severity || 1.0,
                objects: data.detections || [],
                message: `Collision detected on Camera ${data.camera_id}`
            };
            
            this.collisionAlerts.unshift(alert);
            
            // Keep only the most recent alerts
            if (this.collisionAlerts.length > this.maxAlerts) {
                this.collisionAlerts = this.collisionAlerts.slice(0, this.maxAlerts);
            }
            
            // Update alerts display
            this.updateAlertsDisplay();
            
            // Trigger callback
            if (this.onCollisionDetected) {
                this.onCollisionDetected(alert);
            }
            
            // Show visual alert
            this.showCollisionAlert(alert);
            
        } catch (error) {
            console.error('Error handling collision alert:', error);
        }
    }
    
    handleStreamStarted(data) {
        console.log('Camera stream started:', data);
        this.isStreaming = true;
        this.updateConnectionStatus(`Streaming from Camera ${data.camera_id}`);
        this.updateConnectButton('Disconnect', false);
        
        if (this.onCameraConnected) {
            this.onCameraConnected(data.camera_id);
        }
    }
    
    handleStreamStopped(data) {
        console.log('Camera stream stopped:', data);
        this.isStreaming = false;
        this.updateConnectionStatus('Camera disconnected');
        this.updateConnectButton('Connect', false);
        
        // Clear video display
        if (this.liveVideoElement) {
            this.liveVideoElement.src = '';
        }
        
        // Clear overlay
        this.clearCollisionOverlay();
        
        if (this.onCameraDisconnected) {
            this.onCameraDisconnected(data.camera_id);
        }
    }
    
    displayCollisionOverlay(detections) {
        if (!this.liveOverlayElement || !detections || detections.length === 0) {
            this.clearCollisionOverlay();
            return;
        }
        
        // Clear existing overlay
        this.liveOverlayElement.innerHTML = '';
        
        // Add collision markers
        detections.forEach((detection, index) => {
            const marker = document.createElement('div');
            marker.className = 'collision-marker live-collision';
            
            // Position based on collision point or center of detection
            let x = 50, y = 50; // Default center
            
            if (detection.collision_point) {
                x = (detection.collision_point.x || 0.5) * 100;
                y = (detection.collision_point.y || 0.5) * 100;
            }
            
            marker.style.left = `${x}%`;
            marker.style.top = `${y}%`;
            
            marker.innerHTML = `
                <div class="marker-pulse"></div>
                <div class="marker-label">COLLISION!</div>
            `;
            
            this.liveOverlayElement.appendChild(marker);
        });
        
        // Auto-clear overlay after 3 seconds
        setTimeout(() => {
            if (this.liveOverlayElement) {
                this.liveOverlayElement.innerHTML = '';
            }
        }, 3000);
    }
    
    clearCollisionOverlay() {
        if (this.liveOverlayElement) {
            this.liveOverlayElement.innerHTML = '';
        }
    }
    
    showCollisionAlert(alert) {
        // Create temporary alert notification
        const notification = document.createElement('div');
        notification.className = 'collision-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <strong>⚠️ COLLISION DETECTED!</strong>
                <p>Camera ${alert.camera_id} - ${alert.timestamp.toLocaleTimeString()}</p>
                <p>Severity: ${alert.severity.toFixed(2)}</p>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }
    
    updateAlertsDisplay() {
        if (!this.alertsElement) return;
        
        if (this.collisionAlerts.length === 0) {
            this.alertsElement.innerHTML = '<p>No collision alerts</p>';
            return;
        }
        
        let html = '<div class="alerts-container"><h4>Recent Collision Alerts</h4>';
        
        this.collisionAlerts.slice(0, 10).forEach((alert, index) => {
            const timeAgo = this.getTimeAgo(alert.timestamp);
            html += `
                <div class="alert-item ${alert.severity > 0.7 ? 'high-severity' : ''}">
                    <div class="alert-header">
                        <span class="alert-time">${alert.timestamp.toLocaleTimeString()}</span>
                        <span class="alert-camera">Camera ${alert.camera_id}</span>
                        <span class="alert-severity">Severity: ${alert.severity.toFixed(2)}</span>
                    </div>
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-age">${timeAgo}</div>
                </div>
            `;
        });
        
        html += '</div>';
        this.alertsElement.innerHTML = html;
    }
    
    updateConnectionStatus(message) {
        // Update status in alerts element if no specific status element exists
        if (this.alertsElement && !this.isStreaming && this.collisionAlerts.length === 0) {
            this.alertsElement.innerHTML = `<p class="connection-status">${message}</p>`;
        }
        
        console.log('Connection status:', message);
    }
    
    updateConnectButton(text, disabled = false) {
        if (this.connectButtonElement) {
            this.connectButtonElement.textContent = text;
            this.connectButtonElement.disabled = disabled;
        }
    }
    
    updateFrameInfo(metadata) {
        if (!metadata) return;
        
        // Could display frame rate, resolution, etc. in a status area
        // For now, just log for debugging
        if (metadata.frame_count % 30 === 0) { // Log every 30 frames
            console.log(`Frame ${metadata.frame_count} - ${metadata.width}x${metadata.height}`);
        }
    }
    
    getTimeAgo(timestamp) {
        const now = new Date();
        const diff = now - timestamp;
        const seconds = Math.floor(diff / 1000);
        
        if (seconds < 60) return `${seconds}s ago`;
        
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        
        const hours = Math.floor(minutes / 60);
        return `${hours}h ago`;
    }
    
    showError(message) {
        if (this.onError) {
            this.onError(message);
        }
        
        if (this.alertsElement) {
            this.alertsElement.innerHTML = `
                <div class="error-message">
                    <h4>Error</h4>
                    <p>${message}</p>
                </div>
            `;
        }
        
        console.error('LiveFeedViewer Error:', message);
    }
    
    // Public API methods
    setCallbacks(callbacks) {
        this.onCameraConnected = callbacks.onCameraConnected;
        this.onCameraDisconnected = callbacks.onCameraDisconnected;
        this.onCollisionDetected = callbacks.onCollisionDetected;
        this.onError = callbacks.onError;
    }
    
    getCurrentCameraId() {
        return this.currentCameraId;
    }
    
    isCurrentlyStreaming() {
        return this.isStreaming;
    }
    
    getCollisionAlerts(limit = null) {
        return limit ? this.collisionAlerts.slice(0, limit) : [...this.collisionAlerts];
    }
    
    clearAlerts() {
        this.collisionAlerts = [];
        this.updateAlertsDisplay();
    }
    
    disconnect() {
        if (this.isStreaming) {
            this.disconnectCamera();
        }
        
        if (this.socket) {
            if (this.socket.disconnect) {
                this.socket.disconnect();
            } else if (this.socket.close) {
                this.socket.close();
            }
        }
        
        this.isConnected = false;
    }
    
    reconnect() {
        this.disconnect();
        setTimeout(() => this.initializeWebSocket(), 1000);
    }
}

// Global instance for easy access
let liveFeedViewer = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    liveFeedViewer = new LiveFeedViewer();
});