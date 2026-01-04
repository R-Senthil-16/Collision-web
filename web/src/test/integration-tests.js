/**
 * Integration Tests for Web-Backend Communication
 * 
 * Tests video upload, processing workflows, real-time communication,
 * and hardware control integration.
 */

class IntegrationTestSuite {
    constructor() {
        this.apiBase = 'http://localhost:5000/api';
        this.testResults = [];
        this.socket = null;
    }
    
    async runAllTests() {
        console.log('Starting Integration Test Suite...');
        
        // Test API connectivity
        await this.testApiConnectivity();
        
        // Test hardware device listing
        await this.testHardwareDeviceListing();
        
        // Test hardware command sending
        await this.testHardwareCommandSending();
        
        // Test hardware status retrieval
        await this.testHardwareStatusRetrieval();
        
        // Test hardware broadcast functionality
        await this.testHardwareBroadcast();
        
        // Test WebSocket connectivity
        await this.testWebSocketConnection();
        
        // Test real-time hardware updates
        await this.testRealTimeHardwareUpdates();
        
        // Display results
        this.displayResults();
        
        return this.testResults;
    }
    
    async testApiConnectivity() {
        const testName = 'API Connectivity';
        console.log(`Running test: ${testName}`);
        
        try {
            const response = await fetch(`${this.apiBase}/health`);
            const data = await response.json();
            
            if (response.ok && data.status === 'healthy') {
                this.addTestResult(testName, 'PASS', 'API is healthy and responding');
            } else {
                this.addTestResult(testName, 'FAIL', `API returned unexpected response: ${data}`);
            }
        } catch (error) {
            this.addTestResult(testName, 'FAIL', `API connection failed: ${error.message}`);
        }
    }
    
    async testHardwareDeviceListing() {
        const testName = 'Hardware Device Listing';
        console.log(`Running test: ${testName}`);
        
        try {
            const response = await fetch(`${this.apiBase}/hardware/devices`);
            const data = await response.json();
            
            if (response.ok && Array.isArray(data.devices)) {
                const deviceCount = data.devices.length;
                const hasRequiredFields = data.devices.every(device => 
                    device.device_id && 
                    device.ip_address && 
                    device.device_type && 
                    Array.isArray(device.capabilities)
                );
                
                if (hasRequiredFields) {
                    this.addTestResult(testName, 'PASS', `Found ${deviceCount} devices with valid structure`);
                } else {
                    this.addTestResult(testName, 'FAIL', 'Devices missing required fields');
                }
            } else {
                this.addTestResult(testName, 'FAIL', `Invalid response format: ${JSON.stringify(data)}`);
            }
        } catch (error) {
            this.addTestResult(testName, 'FAIL', `Device listing failed: ${error.message}`);
        }
    }
    
    async testHardwareCommandSending() {
        const testName = 'Hardware Command Sending';
        console.log(`Running test: ${testName}`);
        
        try {
            // First get available devices
            const devicesResponse = await fetch(`${this.apiBase}/hardware/devices`);
            const devicesData = await devicesResponse.json();
            
            if (!devicesData.devices || devicesData.devices.length === 0) {
                this.addTestResult(testName, 'SKIP', 'No devices available for testing');
                return;
            }
            
            const testDevice = devicesData.devices[0];
            
            // Send a test command
            const commandResponse = await fetch(`${this.apiBase}/hardware/command`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    device_id: testDevice.device_id,
                    command: 'led_test',
                    parameters: { duration: 1000 }
                })
            });
            
            const commandData = await commandResponse.json();
            
            if (commandResponse.ok && commandData.status === 'sent') {
                this.addTestResult(testName, 'PASS', `Command sent successfully to ${testDevice.device_id}`);
            } else {
                this.addTestResult(testName, 'FAIL', `Command failed: ${commandData.error || 'Unknown error'}`);
            }
        } catch (error) {
            this.addTestResult(testName, 'FAIL', `Command sending failed: ${error.message}`);
        }
    }
    
    async testHardwareStatusRetrieval() {
        const testName = 'Hardware Status Retrieval';
        console.log(`Running test: ${testName}`);
        
        try {
            // Get available devices
            const devicesResponse = await fetch(`${this.apiBase}/hardware/devices`);
            const devicesData = await devicesResponse.json();
            
            if (!devicesData.devices || devicesData.devices.length === 0) {
                this.addTestResult(testName, 'SKIP', 'No devices available for testing');
                return;
            }
            
            const testDevice = devicesData.devices[0];
            
            // Get device status
            const statusResponse = await fetch(`${this.apiBase}/hardware/status/${testDevice.device_id}`);
            const statusData = await statusResponse.json();
            
            if (statusResponse.ok && statusData.device_id === testDevice.device_id) {
                const hasRequiredFields = statusData.status && 
                                        typeof statusData.uptime === 'number' &&
                                        typeof statusData.free_memory === 'number';
                
                if (hasRequiredFields) {
                    this.addTestResult(testName, 'PASS', `Status retrieved for ${testDevice.device_id}`);
                } else {
                    this.addTestResult(testName, 'FAIL', 'Status response missing required fields');
                }
            } else {
                this.addTestResult(testName, 'FAIL', `Status retrieval failed: ${statusData.error || 'Unknown error'}`);
            }
        } catch (error) {
            this.addTestResult(testName, 'FAIL', `Status retrieval failed: ${error.message}`);
        }
    }
    
    async testHardwareBroadcast() {
        const testName = 'Hardware Broadcast';
        console.log(`Running test: ${testName}`);
        
        try {
            const broadcastResponse = await fetch(`${this.apiBase}/hardware/broadcast`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: 'Integration test broadcast',
                    alert_type: 'test'
                })
            });
            
            const broadcastData = await broadcastResponse.json();
            
            if (broadcastResponse.ok && typeof broadcastData.devices_notified === 'number') {
                this.addTestResult(testName, 'PASS', `Broadcast sent to ${broadcastData.devices_notified} devices`);
            } else {
                this.addTestResult(testName, 'FAIL', `Broadcast failed: ${broadcastData.error || 'Unknown error'}`);
            }
        } catch (error) {
            this.addTestResult(testName, 'FAIL', `Broadcast failed: ${error.message}`);
        }
    }
    
    async testWebSocketConnection() {
        const testName = 'WebSocket Connection';
        console.log(`Running test: ${testName}`);
        
        return new Promise((resolve) => {
            try {
                this.socket = io('http://localhost:5000', {
                    transports: ['websocket', 'polling']
                });
                
                const timeout = setTimeout(() => {
                    this.addTestResult(testName, 'FAIL', 'WebSocket connection timeout');
                    resolve();
                }, 5000);
                
                this.socket.on('connect', () => {
                    clearTimeout(timeout);
                    this.addTestResult(testName, 'PASS', 'WebSocket connected successfully');
                    resolve();
                });
                
                this.socket.on('connect_error', (error) => {
                    clearTimeout(timeout);
                    this.addTestResult(testName, 'FAIL', `WebSocket connection error: ${error.message}`);
                    resolve();
                });
                
            } catch (error) {
                this.addTestResult(testName, 'FAIL', `WebSocket setup failed: ${error.message}`);
                resolve();
            }
        });
    }
    
    async testRealTimeHardwareUpdates() {
        const testName = 'Real-time Hardware Updates';
        console.log(`Running test: ${testName}`);
        
        if (!this.socket || !this.socket.connected) {
            this.addTestResult(testName, 'SKIP', 'WebSocket not connected');
            return;
        }
        
        return new Promise((resolve) => {
            const timeout = setTimeout(() => {
                this.addTestResult(testName, 'FAIL', 'No device status response received');
                resolve();
            }, 5000);
            
            // Listen for device status response
            this.socket.on('all_device_status', (data) => {
                clearTimeout(timeout);
                
                if (data.type === 'all_device_status' && data.devices) {
                    const deviceCount = Object.keys(data.devices).length;
                    this.addTestResult(testName, 'PASS', `Received status for ${deviceCount} devices via WebSocket`);
                } else {
                    this.addTestResult(testName, 'FAIL', 'Invalid device status format');
                }
                resolve();
            });
            
            // Request device status
            this.socket.emit('request_device_status', {});
        });
    }
    
    addTestResult(testName, status, message) {
        const result = {
            test: testName,
            status: status,
            message: message,
            timestamp: new Date().toISOString()
        };
        
        this.testResults.push(result);
        console.log(`${status}: ${testName} - ${message}`);
    }
    
    displayResults() {
        console.log('\n=== Integration Test Results ===');
        
        const passed = this.testResults.filter(r => r.status === 'PASS').length;
        const failed = this.testResults.filter(r => r.status === 'FAIL').length;
        const skipped = this.testResults.filter(r => r.status === 'SKIP').length;
        
        console.log(`Total Tests: ${this.testResults.length}`);
        console.log(`Passed: ${passed}`);
        console.log(`Failed: ${failed}`);
        console.log(`Skipped: ${skipped}`);
        
        console.log('\nDetailed Results:');
        this.testResults.forEach(result => {
            const status = result.status === 'PASS' ? '✅' : 
                          result.status === 'FAIL' ? '❌' : '⏭️';
            console.log(`${status} ${result.test}: ${result.message}`);
        });
        
        // Create results summary for display
        this.createResultsDisplay();
        
        // Cleanup
        if (this.socket) {
            this.socket.disconnect();
        }
    }
    
    createResultsDisplay() {
        // Create a results display in the DOM if we're in a browser environment
        if (typeof document !== 'undefined') {
            const resultsContainer = document.getElementById('test-results') || 
                                   this.createResultsContainer();
            
            const passed = this.testResults.filter(r => r.status === 'PASS').length;
            const failed = this.testResults.filter(r => r.status === 'FAIL').length;
            const skipped = this.testResults.filter(r => r.status === 'SKIP').length;
            
            resultsContainer.innerHTML = `
                <h3>Integration Test Results</h3>
                <div class="test-summary">
                    <span class="test-stat passed">Passed: ${passed}</span>
                    <span class="test-stat failed">Failed: ${failed}</span>
                    <span class="test-stat skipped">Skipped: ${skipped}</span>
                </div>
                <div class="test-details">
                    ${this.testResults.map(result => `
                        <div class="test-result ${result.status.toLowerCase()}">
                            <span class="test-name">${result.test}</span>
                            <span class="test-status">${result.status}</span>
                            <span class="test-message">${result.message}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }
    }
    
    createResultsContainer() {
        const container = document.createElement('div');
        container.id = 'test-results';
        container.className = 'integration-test-results';
        
        // Add some basic styling
        const style = document.createElement('style');
        style.textContent = `
            .integration-test-results {
                margin: 2rem;
                padding: 1rem;
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: #f9f9f9;
                font-family: monospace;
            }
            .test-summary {
                margin-bottom: 1rem;
                display: flex;
                gap: 1rem;
            }
            .test-stat {
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                font-weight: bold;
            }
            .test-stat.passed { background-color: #d4edda; color: #155724; }
            .test-stat.failed { background-color: #f8d7da; color: #721c24; }
            .test-stat.skipped { background-color: #fff3cd; color: #856404; }
            .test-result {
                display: grid;
                grid-template-columns: 2fr 1fr 3fr;
                gap: 1rem;
                padding: 0.5rem;
                border-bottom: 1px solid #eee;
                align-items: center;
            }
            .test-result.pass { background-color: #f8fff8; }
            .test-result.fail { background-color: #fff8f8; }
            .test-result.skip { background-color: #fffef8; }
            .test-name { font-weight: bold; }
            .test-status { 
                text-align: center;
                padding: 0.25rem;
                border-radius: 4px;
                font-weight: bold;
            }
            .test-result.pass .test-status { background-color: #28a745; color: white; }
            .test-result.fail .test-status { background-color: #dc3545; color: white; }
            .test-result.skip .test-status { background-color: #ffc107; color: black; }
        `;
        
        document.head.appendChild(style);
        document.body.appendChild(container);
        
        return container;
    }
}

// Auto-run tests if in browser environment and page is loaded
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        // Add a button to run tests manually
        const testButton = document.createElement('button');
        testButton.textContent = 'Run Integration Tests';
        testButton.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 1000;
            padding: 0.5rem 1rem;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        `;
        
        testButton.addEventListener('click', async () => {
            testButton.disabled = true;
            testButton.textContent = 'Running Tests...';
            
            const testSuite = new IntegrationTestSuite();
            await testSuite.runAllTests();
            
            testButton.disabled = false;
            testButton.textContent = 'Run Integration Tests';
        });
        
        document.body.appendChild(testButton);
    });
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = IntegrationTestSuite;
}

// Make available globally
if (typeof window !== 'undefined') {
    window.IntegrationTestSuite = IntegrationTestSuite;
}