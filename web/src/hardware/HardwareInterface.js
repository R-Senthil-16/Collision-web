/**
 * Hardware Interface for ESP8266 Device Management
 * 
 * Provides functionality to manage ESP8266 devices, send commands,
 * monitor status, and display hardware control interface.
 */

class HardwareInterface {
    constructor() {
        this.devices = new Map();
        this.socket = null;
        this.isConnected = false;
        this.callbacks = {
            onDeviceUpdate: null,
            onCommandResponse: null,
            onError: null
        };
        
        // API endpoints
        this.apiBase = '/api';
        this.endpoints = {
            devices: `${this.apiBase}/hardware/devices`,
            command: `${this.apiBase}/hardware/command`,
            broadcast: `${this.apiBase}/hardware/broadcast`,
            status: `${this.apiBase}/hardware/status`,
            logs: `${this.apiBase}/hardware/logs`,
            statistics: `${this.apiBase}/hardware/statistics`,
            discover: `${this.apiBase}/hardware/discover`
        };
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }
    
    initialize() {
        console.log('Initializing Hardware Interface...');
        
        // Set up UI event handlers
        this.setupEventHandlers();
        
        // Connect to WebSocket for real-time updates
        this.connectWebSocket();
        
        // Load initial device list
        this.refreshDeviceList();
        
        // Set up periodic status updates
        this.startStatusUpdates();
    }
    
    setupEventHandlers() {
        // Manual control buttons
        const testLeds = document.getElementById('test-leds');
        const testServos = document.getElementById('test-servos');
        const testRelays = document.getElementById('test-relays');
        
        if (testLeds) {
            testLeds.addEventListener('click', () => this.testAllDevices('led_test'));
        }
        
        if (testServos) {
            testServos.addEventListener('click', () => this.testAllDevices('servo_test'));
        }
        
        if (testRelays) {
            testRelays.addEventListener('click', () => this.testAllDevices('relay_test'));
        }
        
        // Add refresh button functionality
        this.addRefreshButton();
        
        // Add device discovery button
        this.addDiscoveryButton();
    }
    
    addRefreshButton() {
        const deviceList = document.querySelector('.device-list');
        if (deviceList && !document.getElementById('refresh-devices')) {
            const refreshButton = document.createElement('button');
            refreshButton.id = 'refresh-devices';
            refreshButton.textContent = 'Refresh Devices';
            refreshButton.className = 'btn btn-secondary';
            refreshButton.addEventListener('click', () => this.refreshDeviceList());
            
            const h3 = deviceList.querySelector('h3');
            if (h3) {
                h3.insertAdjacentElement('afterend', refreshButton);
            }
        }
    }
    
    addDiscoveryButton() {
        const deviceList = document.querySelector('.device-list');
        if (deviceList && !document.getElementById('discover-devices')) {
            const discoverButton = document.createElement('button');
            discoverButton.id = 'discover-devices';
            discoverButton.textContent = 'Discover New Devices';
            discoverButton.className = 'btn btn-primary';
            discoverButton.addEventListener('click', () => this.discoverDevices());
            
            const refreshButton = document.getElementById('refresh-devices');
            if (refreshButton) {
                refreshButton.insertAdjacentElement('afterend', discoverButton);
            }
        }
    }
    
    connectWebSocket() {
        try {
            // Connect to WebSocket for real-time hardware updates
            this.socket = io('/', {
                transports: ['websocket', 'polling']
            });
            
            this.socket.on('connect', () => {
                console.log('Connected to hardware WebSocket');
                this.isConnected = true;
                this.updateConnectionStatus(true);
                
                // Join hardware room for targeted updates
                this.socket.emit('join_room', { room: 'hardware' });
            });
            
            this.socket.on('disconnect', () => {
                console.log('Disconnected from hardware WebSocket');
                this.isConnected = false;
                this.updateConnectionStatus(false);
            });
            
            this.socket.on('hardware_status', (data) => {
                this.handleDeviceStatusUpdate(data);
            });
            
            this.socket.on('hardware_command_result', (data) => {
                this.handleCommandResponse(data);
            });
            
            this.socket.on('device_status', (data) => {
                this.handleDeviceStatusUpdate(data);
            });
            
            this.socket.on('all_device_status', (data) => {
                this.handleAllDeviceStatusUpdate(data);
            });
            
            this.socket.on('status_update', (data) => {
                if (data.type === 'status_update') {
                    this.handleStatusUpdate(data.data);
                }
            });
            
            this.socket.on('error', (data) => {
                console.error('WebSocket error:', data);
                this.logMessage(`WebSocket error: ${data.message}`, 'error');
            });
            
        } catch (error) {
            console.warn('WebSocket connection failed, using polling mode:', error);
            this.isConnected = false;
        }
    }
    
    async refreshDeviceList() {
        try {
            const response = await fetch(this.endpoints.devices);
            const data = await response.json();
            
            if (response.ok) {
                this.updateDeviceDisplay(data.devices);
                this.logMessage(`Loaded ${data.total_devices} devices`);
            } else {
                throw new Error(data.error || 'Failed to load devices');
            }
        } catch (error) {
            console.error('Failed to refresh device list:', error);
            this.logMessage(`Error loading devices: ${error.message}`, 'error');
        }
    }
    
    async discoverDevices() {
        try {
            const discoverButton = document.getElementById('discover-devices');
            if (discoverButton) {
                discoverButton.disabled = true;
                discoverButton.textContent = 'Discovering...';
            }
            
            const response = await fetch(this.endpoints.discover, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (response.ok) {
                this.logMessage(`Discovery complete: Found ${data.devices_found} devices`);
                await this.refreshDeviceList();
            } else {
                throw new Error(data.error || 'Device discovery failed');
            }
        } catch (error) {
            console.error('Device discovery failed:', error);
            this.logMessage(`Discovery failed: ${error.message}`, 'error');
        } finally {
            const discoverButton = document.getElementById('discover-devices');
            if (discoverButton) {
                discoverButton.disabled = false;
                discoverButton.textContent = 'Discover New Devices';
            }
        }
    }
    
    updateDeviceDisplay(devices) {
        const deviceStatus = document.getElementById('device-status');
        if (!deviceStatus) return;
        
        if (devices.length === 0) {
            deviceStatus.innerHTML = `
                <div class="no-devices">
                    <p>No ESP8266 devices connected.</p>
                    <p>Click "Discover New Devices" to search for devices on the network.</p>
                </div>
            `;
            return;
        }
        
        // Store devices for later reference
        devices.forEach(device => {
            this.devices.set(device.device_id, device);
        });
        
        const deviceHTML = devices.map(device => this.createDeviceCard(device)).join('');
        deviceStatus.innerHTML = `
            <div class="devices-grid">
                ${deviceHTML}
            </div>
        `;
        
        // Add event listeners to device control buttons
        this.setupDeviceControls();
    }
    
    createDeviceCard(device) {
        const statusClass = device.status === 'online' ? 'status-online' : 'status-offline';
        const healthInfo = device.health ? `
            <div class="health-info">
                <span class="health-score">Health: ${Math.round(device.health.overall_health * 100)}%</span>
                <span class="connectivity">Signal: ${Math.round(device.health.connectivity_score * 100)}%</span>
            </div>
        ` : '';
        
        return `
            <div class="device-card" data-device-id="${device.device_id}">
                <div class="device-header">
                    <h4>${device.device_id}</h4>
                    <span class="device-status ${statusClass}">${device.status}</span>
                </div>
                <div class="device-info">
                    <p><strong>IP:</strong> ${device.ip_address}</p>
                    <p><strong>Type:</strong> ${device.device_type}</p>
                    <p><strong>Capabilities:</strong> ${device.capabilities.join(', ')}</p>
                    ${healthInfo}
                </div>
                <div class="device-controls">
                    <button class="btn btn-sm btn-primary" onclick="hardwareInterface.sendDeviceCommand('${device.device_id}', 'led_on')">LED On</button>
                    <button class="btn btn-sm btn-secondary" onclick="hardwareInterface.sendDeviceCommand('${device.device_id}', 'led_off')">LED Off</button>
                    <button class="btn btn-sm btn-info" onclick="hardwareInterface.getDeviceStatus('${device.device_id}')">Status</button>
                    <button class="btn btn-sm btn-warning" onclick="hardwareInterface.showDeviceLogs('${device.device_id}')">Logs</button>
                </div>
            </div>
        `;
    }
    
    setupDeviceControls() {
        // Device controls are handled by onclick attributes in createDeviceCard
        // This method can be used for additional setup if needed
    }
    
    async sendDeviceCommand(deviceId, command, parameters = {}) {
        try {
            const response = await fetch(this.endpoints.command, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    device_id: deviceId,
                    command: command,
                    parameters: parameters
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.logMessage(`Command sent to ${deviceId}: ${command}`);
                if (this.callbacks.onCommandResponse) {
                    this.callbacks.onCommandResponse(data);
                }
            } else {
                throw new Error(data.error || 'Command failed');
            }
        } catch (error) {
            console.error('Command failed:', error);
            this.logMessage(`Command failed for ${deviceId}: ${error.message}`, 'error');
        }
    }
    
    async testAllDevices(testType) {
        const devices = Array.from(this.devices.values()).filter(d => d.status === 'online');
        
        if (devices.length === 0) {
            this.logMessage('No online devices to test', 'warning');
            return;
        }
        
        this.logMessage(`Testing ${testType} on ${devices.length} devices...`);
        
        const promises = devices.map(device => 
            this.sendDeviceCommand(device.device_id, testType)
        );
        
        try {
            await Promise.all(promises);
            this.logMessage(`${testType} test completed on all devices`);
        } catch (error) {
            this.logMessage(`Some ${testType} tests failed`, 'warning');
        }
    }
    
    async getDeviceStatus(deviceId) {
        try {
            const response = await fetch(`${this.endpoints.status}/${deviceId}`);
            const data = await response.json();
            
            if (response.ok) {
                this.showDeviceStatusModal(data);
            } else {
                throw new Error(data.error || 'Failed to get device status');
            }
        } catch (error) {
            console.error('Failed to get device status:', error);
            this.logMessage(`Failed to get status for ${deviceId}: ${error.message}`, 'error');
        }
    }
    
    async showDeviceLogs(deviceId) {
        try {
            const response = await fetch(`${this.endpoints.logs}/${deviceId}?limit=20`);
            const data = await response.json();
            
            if (response.ok) {
                this.showDeviceLogsModal(deviceId, data);
            } else {
                throw new Error(data.error || 'Failed to get device logs');
            }
        } catch (error) {
            console.error('Failed to get device logs:', error);
            this.logMessage(`Failed to get logs for ${deviceId}: ${error.message}`, 'error');
        }
    }
    
    showDeviceStatusModal(statusData) {
        // Create modal for device status
        const modal = this.createModal('Device Status', `
            <div class="device-status-details">
                <h4>Device: ${statusData.device_id}</h4>
                <div class="status-grid">
                    <div class="status-item">
                        <label>Status:</label>
                        <span class="status-value">${statusData.status}</span>
                    </div>
                    <div class="status-item">
                        <label>Uptime:</label>
                        <span class="status-value">${Math.floor(statusData.uptime / 1000)}s</span>
                    </div>
                    <div class="status-item">
                        <label>Free Memory:</label>
                        <span class="status-value">${statusData.free_memory} bytes</span>
                    </div>
                    <div class="status-item">
                        <label>WiFi Strength:</label>
                        <span class="status-value">${statusData.wifi_strength} dBm</span>
                    </div>
                </div>
                ${statusData.health_metrics ? `
                    <h5>Health Metrics</h5>
                    <div class="health-grid">
                        <div class="health-item">
                            <label>Overall Health:</label>
                            <span class="health-value">${Math.round(statusData.health_metrics.overall_health * 100)}%</span>
                        </div>
                        <div class="health-item">
                            <label>Connectivity:</label>
                            <span class="health-value">${Math.round(statusData.health_metrics.connectivity_score * 100)}%</span>
                        </div>
                        <div class="health-item">
                            <label>Performance:</label>
                            <span class="health-value">${Math.round(statusData.health_metrics.performance_score * 100)}%</span>
                        </div>
                        <div class="health-item">
                            <label>Error Count:</label>
                            <span class="health-value">${statusData.health_metrics.error_count}</span>
                        </div>
                    </div>
                ` : ''}
                ${Object.keys(statusData.sensor_data).length > 0 ? `
                    <h5>Sensor Data</h5>
                    <div class="sensor-grid">
                        ${Object.entries(statusData.sensor_data).map(([key, value]) => `
                            <div class="sensor-item">
                                <label>${key}:</label>
                                <span class="sensor-value">${value}</span>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `);
        
        document.body.appendChild(modal);
    }
    
    showDeviceLogsModal(deviceId, logsData) {
        const commandLogs = logsData.command_logs.slice(0, 10);
        const deviceLogs = logsData.device_logs.slice(0, 10);
        
        const modal = this.createModal(`Device Logs - ${deviceId}`, `
            <div class="device-logs">
                <h5>Recent Commands (${commandLogs.length})</h5>
                <div class="logs-container">
                    ${commandLogs.map(log => `
                        <div class="log-entry command-log">
                            <span class="log-time">${new Date(log.timestamp * 1000).toLocaleTimeString()}</span>
                            <span class="log-action">${log.action}</span>
                            <span class="log-status status-${log.status}">${log.status}</span>
                        </div>
                    `).join('')}
                </div>
                
                <h5>Device Events (${deviceLogs.length})</h5>
                <div class="logs-container">
                    ${deviceLogs.map(log => `
                        <div class="log-entry device-log">
                            <span class="log-time">${new Date(log.timestamp * 1000).toLocaleTimeString()}</span>
                            <span class="log-event">${log.event_type}</span>
                            <span class="log-severity severity-${log.severity}">${log.severity}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `);
        
        document.body.appendChild(modal);
    }
    
    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
            </div>
        `;
        
        // Close modal functionality
        const closeBtn = modal.querySelector('.modal-close');
        const overlay = modal;
        
        closeBtn.addEventListener('click', () => modal.remove());
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) modal.remove();
        });
        
        return modal;
    }
    
    handleDeviceStatusUpdate(data) {
        if (data.type === 'hardware_update') {
            const device = this.devices.get(data.device_id);
            if (device) {
                // Update device status
                Object.assign(device, data.status);
                
                // Update UI if device card is visible
                const deviceCard = document.querySelector(`[data-device-id="${data.device_id}"]`);
                if (deviceCard) {
                    this.updateDeviceCard(deviceCard, device);
                }
            }
        } else if (data.type === 'device_status' && data.device_id) {
            // Handle individual device status update
            const device = this.devices.get(data.device_id);
            if (device && data.status) {
                Object.assign(device, data.status);
                
                const deviceCard = document.querySelector(`[data-device-id="${data.device_id}"]`);
                if (deviceCard) {
                    this.updateDeviceCard(deviceCard, device);
                }
            }
        }
        
        if (this.callbacks.onDeviceUpdate) {
            this.callbacks.onDeviceUpdate(data);
        }
    }
    
    handleAllDeviceStatusUpdate(data) {
        if (data.type === 'all_device_status' && data.devices) {
            // Update all device statuses
            Object.entries(data.devices).forEach(([deviceId, deviceData]) => {
                const device = this.devices.get(deviceId);
                if (device && deviceData.status) {
                    Object.assign(device, deviceData.status);
                    
                    const deviceCard = document.querySelector(`[data-device-id="${deviceId}"]`);
                    if (deviceCard) {
                        this.updateDeviceCard(deviceCard, device);
                    }
                }
            });
        }
    }
    
    handleStatusUpdate(data) {
        // Handle general status updates
        this.logMessage(`Status update: ${JSON.stringify(data)}`);
    }
    
    handleCommandResponse(data) {
        if (data.type === 'command_result') {
            const status = data.success ? 'success' : 'failed';
            this.logMessage(`Command ${data.command} on ${data.device_id}: ${status}`);
        }
        
        if (this.callbacks.onCommandResponse) {
            this.callbacks.onCommandResponse(data);
        }
    }
    
    handleDeviceDiscovered(data) {
        this.logMessage(`New device discovered: ${data.device_id}`);
        this.refreshDeviceList();
    }
    
    handleDeviceDisconnected(data) {
        this.logMessage(`Device disconnected: ${data.device_id}`, 'warning');
        
        const device = this.devices.get(data.device_id);
        if (device) {
            device.status = 'offline';
            
            const deviceCard = document.querySelector(`[data-device-id="${data.device_id}"]`);
            if (deviceCard) {
                this.updateDeviceCard(deviceCard, device);
            }
        }
    }
    
    updateDeviceCard(cardElement, device) {
        const statusElement = cardElement.querySelector('.device-status');
        if (statusElement) {
            statusElement.textContent = device.status;
            statusElement.className = `device-status ${device.status === 'online' ? 'status-online' : 'status-offline'}`;
        }
        
        // Update health info if available
        const healthInfo = cardElement.querySelector('.health-info');
        if (healthInfo && device.health) {
            healthInfo.innerHTML = `
                <span class="health-score">Health: ${Math.round(device.health.overall_health * 100)}%</span>
                <span class="connectivity">Signal: ${Math.round(device.health.connectivity_score * 100)}%</span>
            `;
        }
    }
    
    updateConnectionStatus(connected) {
        const statusIndicator = document.getElementById('hardware-connection-status');
        if (statusIndicator) {
            statusIndicator.textContent = connected ? 'Connected' : 'Disconnected';
            statusIndicator.className = connected ? 'status-connected' : 'status-disconnected';
        }
    }
    
    startStatusUpdates() {
        // Refresh device list every 30 seconds
        setInterval(() => {
            if (this.devices.size > 0) {
                this.refreshDeviceList();
            }
        }, 30000);
        
        // Request real-time status updates via WebSocket if connected
        if (this.isConnected && this.socket) {
            setInterval(() => {
                this.socket.emit('request_device_status', {});
            }, 10000); // Request status every 10 seconds
        }
    }
    
    logMessage(message, type = 'info') {
        const logsDiv = document.getElementById('hardware-logs');
        if (logsDiv) {
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${type}`;
            logEntry.innerHTML = `
                <span class="log-timestamp">${timestamp}</span>
                <span class="log-message">${message}</span>
            `;
            
            logsDiv.appendChild(logEntry);
            
            // Keep only last 50 log entries
            const entries = logsDiv.querySelectorAll('.log-entry');
            if (entries.length > 50) {
                entries[0].remove();
            }
            
            // Scroll to bottom
            logsDiv.scrollTop = logsDiv.scrollHeight;
        }
        
        console.log(`[Hardware] ${message}`);
    }
    
    setCallbacks(callbacks) {
        Object.assign(this.callbacks, callbacks);
    }
    
    // Public API methods
    async broadcastAlert(message, alertType = 'collision') {
        try {
            const response = await fetch(this.endpoints.broadcast, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    alert_type: alertType
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.logMessage(`Alert broadcast to ${data.devices_notified} devices: ${message}`);
                return true;
            } else {
                throw new Error(data.error || 'Broadcast failed');
            }
        } catch (error) {
            console.error('Broadcast failed:', error);
            this.logMessage(`Broadcast failed: ${error.message}`, 'error');
            return false;
        }
    }
    
    getConnectedDevices() {
        return Array.from(this.devices.values()).filter(d => d.status === 'online');
    }
    
    getDeviceCount() {
        return this.devices.size;
    }
    
    isDeviceOnline(deviceId) {
        const device = this.devices.get(deviceId);
        return device && device.status === 'online';
    }
}

// Create global instance
const hardwareInterface = new HardwareInterface();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HardwareInterface;
}