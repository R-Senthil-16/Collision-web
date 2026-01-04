/**
 * Monitoring Dashboard for System Health and Performance
 */

class MonitoringDashboard {
    constructor() {
        this.baseUrl = 'http://localhost:5000/api';
        this.updateInterval = 10000; // 10 seconds
        this.updateTimer = null;
        this.charts = {};
        
        this.init();
    }
    
    init() {
        this.createDashboardHTML();
        this.setupEventListeners();
        this.startAutoUpdate();
        
        console.log('Monitoring Dashboard initialized');
    }
    
    createDashboardHTML() {
        const monitoringPanel = document.getElementById('monitoring-panel');
        if (!monitoringPanel) {
            console.warn('Monitoring panel not found');
            return;
        }
        
        monitoringPanel.innerHTML = `
            <div class="monitoring-dashboard">
                <div class="dashboard-header">
                    <h2>System Monitoring Dashboard</h2>
                    <div class="dashboard-controls">
                        <button id="refresh-dashboard" class="btn btn-primary">Refresh</button>
                        <button id="toggle-auto-update" class="btn btn-secondary">Auto Update: ON</button>
                        <select id="update-interval" class="form-select">
                            <option value="5000">5 seconds</option>
                            <option value="10000" selected>10 seconds</option>
                            <option value="30000">30 seconds</option>
                            <option value="60000">1 minute</option>
                        </select>
                    </div>
                </div>
                
                <div class="system-overview">
                    <div class="status-cards">
                        <div class="status-card" id="overall-health">
                            <h3>Overall Health</h3>
                            <div class="status-indicator unknown">Unknown</div>
                            <div class="status-details">Checking...</div>
                        </div>
                        
                        <div class="status-card" id="cpu-usage">
                            <h3>CPU Usage</h3>
                            <div class="metric-value">--</div>
                            <div class="metric-chart" id="cpu-chart"></div>
                        </div>
                        
                        <div class="status-card" id="memory-usage">
                            <h3>Memory Usage</h3>
                            <div class="metric-value">--</div>
                            <div class="metric-chart" id="memory-chart"></div>
                        </div>
                        
                        <div class="status-card" id="disk-usage">
                            <h3>Disk Usage</h3>
                            <div class="metric-value">--</div>
                            <div class="metric-chart" id="disk-chart"></div>
                        </div>
                    </div>
                </div>
                
                <div class="monitoring-sections">
                    <div class="monitoring-section">
                        <h3>Component Status</h3>
                        <div id="component-status" class="component-grid">
                            <div class="loading">Loading component status...</div>
                        </div>
                    </div>
                    
                    <div class="monitoring-section">
                        <h3>Active Alerts</h3>
                        <div id="active-alerts" class="alerts-container">
                            <div class="loading">Loading alerts...</div>
                        </div>
                    </div>
                    
                    <div class="monitoring-section">
                        <h3>Performance History</h3>
                        <div class="chart-controls">
                            <select id="history-duration">
                                <option value="15">Last 15 minutes</option>
                                <option value="60" selected>Last hour</option>
                                <option value="240">Last 4 hours</option>
                                <option value="1440">Last 24 hours</option>
                            </select>
                        </div>
                        <div id="performance-chart" class="performance-chart">
                            <canvas id="performance-canvas" width="800" height="300"></canvas>
                        </div>
                    </div>
                    
                    <div class="monitoring-section">
                        <h3>System Logs</h3>
                        <div class="log-controls">
                            <select id="log-type">
                                <option value="system">System</option>
                                <option value="performance">Performance</option>
                                <option value="errors">Errors</option>
                                <option value="alerts">Alerts</option>
                            </select>
                            <select id="log-lines">
                                <option value="50">50 lines</option>
                                <option value="100" selected>100 lines</option>
                                <option value="200">200 lines</option>
                                <option value="500">500 lines</option>
                            </select>
                            <button id="refresh-logs" class="btn btn-secondary">Refresh Logs</button>
                        </div>
                        <div id="system-logs" class="logs-container">
                            <div class="loading">Loading logs...</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.addDashboardStyles();
    }
    
    addDashboardStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .monitoring-dashboard {
                padding: 20px;
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .dashboard-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 2px solid #e0e0e0;
            }
            
            .dashboard-controls {
                display: flex;
                gap: 10px;
                align-items: center;
            }
            
            .status-cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .status-card {
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .status-card h3 {
                margin: 0 0 15px 0;
                color: #333;
                font-size: 16px;
            }
            
            .status-indicator {
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                text-align: center;
                margin-bottom: 10px;
            }
            
            .status-indicator.healthy {
                background: #d4edda;
                color: #155724;
            }
            
            .status-indicator.warning {
                background: #fff3cd;
                color: #856404;
            }
            
            .status-indicator.error {
                background: #f8d7da;
                color: #721c24;
            }
            
            .status-indicator.critical {
                background: #f5c6cb;
                color: #721c24;
            }
            
            .status-indicator.unknown {
                background: #e2e3e5;
                color: #383d41;
            }
            
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                color: #007bff;
                margin-bottom: 10px;
            }
            
            .metric-chart {
                height: 40px;
                background: #f8f9fa;
                border-radius: 4px;
                position: relative;
                overflow: hidden;
            }
            
            .monitoring-sections {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
            }
            
            .monitoring-section {
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .monitoring-section:nth-child(3),
            .monitoring-section:nth-child(4) {
                grid-column: 1 / -1;
            }
            
            .monitoring-section h3 {
                margin: 0 0 20px 0;
                color: #333;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            
            .component-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
            }
            
            .component-item {
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: #f8f9fa;
            }
            
            .component-name {
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            .component-status {
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }
            
            .alerts-container {
                max-height: 300px;
                overflow-y: auto;
            }
            
            .alert-item {
                padding: 10px;
                margin-bottom: 10px;
                border-left: 4px solid;
                background: #f8f9fa;
                border-radius: 0 4px 4px 0;
            }
            
            .alert-item.critical {
                border-left-color: #dc3545;
            }
            
            .alert-item.error {
                border-left-color: #fd7e14;
            }
            
            .alert-item.warning {
                border-left-color: #ffc107;
            }
            
            .alert-item.info {
                border-left-color: #17a2b8;
            }
            
            .alert-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 5px;
            }
            
            .alert-severity {
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
            }
            
            .chart-controls,
            .log-controls {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
                align-items: center;
            }
            
            .performance-chart {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
            }
            
            .logs-container {
                background: #1e1e1e;
                color: #f8f8f2;
                padding: 15px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                max-height: 400px;
                overflow-y: auto;
                white-space: pre-wrap;
            }
            
            .loading {
                text-align: center;
                color: #666;
                font-style: italic;
                padding: 20px;
            }
            
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }
            
            .btn-primary {
                background: #007bff;
                color: white;
            }
            
            .btn-secondary {
                background: #6c757d;
                color: white;
            }
            
            .btn:hover {
                opacity: 0.9;
            }
            
            .form-select {
                padding: 6px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-dashboard')?.addEventListener('click', () => {
            this.updateDashboard();
        });
        
        // Auto-update toggle
        document.getElementById('toggle-auto-update')?.addEventListener('click', (e) => {
            this.toggleAutoUpdate();
        });
        
        // Update interval change
        document.getElementById('update-interval')?.addEventListener('change', (e) => {
            this.updateInterval = parseInt(e.target.value);
            if (this.updateTimer) {
                this.startAutoUpdate();
            }
        });
        
        // History duration change
        document.getElementById('history-duration')?.addEventListener('change', () => {
            this.updatePerformanceChart();
        });
        
        // Log controls
        document.getElementById('refresh-logs')?.addEventListener('click', () => {
            this.updateSystemLogs();
        });
        
        document.getElementById('log-type')?.addEventListener('change', () => {
            this.updateSystemLogs();
        });
        
        document.getElementById('log-lines')?.addEventListener('change', () => {
            this.updateSystemLogs();
        });
    }
    
    startAutoUpdate() {
        this.stopAutoUpdate();
        this.updateDashboard();
        
        this.updateTimer = setInterval(() => {
            this.updateDashboard();
        }, this.updateInterval);
    }
    
    stopAutoUpdate() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    }
    
    toggleAutoUpdate() {
        const button = document.getElementById('toggle-auto-update');
        
        if (this.updateTimer) {
            this.stopAutoUpdate();
            button.textContent = 'Auto Update: OFF';
            button.classList.remove('btn-primary');
            button.classList.add('btn-secondary');
        } else {
            this.startAutoUpdate();
            button.textContent = 'Auto Update: ON';
            button.classList.remove('btn-secondary');
            button.classList.add('btn-primary');
        }
    }
    
    async updateDashboard() {
        try {
            await Promise.all([
                this.updateSystemHealth(),
                this.updateComponentStatus(),
                this.updateActiveAlerts(),
                this.updatePerformanceChart(),
                this.updateSystemLogs()
            ]);
        } catch (error) {
            console.error('Dashboard update failed:', error);
        }
    }
    
    async updateSystemHealth() {
        try {
            const response = await fetch(`${this.baseUrl}/system/health`);
            const health = await response.json();
            
            // Update overall health
            const healthCard = document.getElementById('overall-health');
            const indicator = healthCard.querySelector('.status-indicator');
            const details = healthCard.querySelector('.status-details');
            
            indicator.className = `status-indicator ${health.overall_status}`;
            indicator.textContent = health.overall_status.charAt(0).toUpperCase() + health.overall_status.slice(1);
            
            details.innerHTML = `
                <div>CPU: ${health.system_metrics.cpu_usage.toFixed(1)}%</div>
                <div>Memory: ${health.system_metrics.memory_usage.toFixed(1)}%</div>
                <div>Alerts: ${health.active_alerts}</div>
            `;
            
            // Update metric cards
            this.updateMetricCard('cpu-usage', health.system_metrics.cpu_usage, '%');
            this.updateMetricCard('memory-usage', health.system_metrics.memory_usage, '%');
            this.updateMetricCard('disk-usage', health.system_metrics.disk_usage, '%');
            
        } catch (error) {
            console.error('Failed to update system health:', error);
        }
    }
    
    updateMetricCard(cardId, value, unit) {
        const card = document.getElementById(cardId);
        const metricValue = card.querySelector('.metric-value');
        
        metricValue.textContent = `${value.toFixed(1)}${unit}`;
        
        // Update color based on value
        if (value > 80) {
            metricValue.style.color = '#dc3545';
        } else if (value > 60) {
            metricValue.style.color = '#ffc107';
        } else {
            metricValue.style.color = '#28a745';
        }
    }
    
    async updateComponentStatus() {
        try {
            const response = await fetch(`${this.baseUrl}/system/components`);
            const data = await response.json();
            
            const container = document.getElementById('component-status');
            
            if (Object.keys(data.components).length === 0) {
                container.innerHTML = '<div class="loading">No components found</div>';
                return;
            }
            
            container.innerHTML = Object.entries(data.components).map(([name, status]) => `
                <div class="component-item">
                    <div class="component-name">${name.replace(/_/g, ' ').toUpperCase()}</div>
                    <div class="component-status ${status.status}">${status.status}</div>
                    <div class="component-details">
                        <small>Last update: ${new Date(status.last_update * 1000).toLocaleTimeString()}</small>
                        ${status.error_count > 0 ? `<br><small>Errors: ${status.error_count}</small>` : ''}
                    </div>
                </div>
            `).join('');
            
        } catch (error) {
            console.error('Failed to update component status:', error);
        }
    }
    
    async updateActiveAlerts() {
        try {
            const response = await fetch(`${this.baseUrl}/system/alerts?limit=10`);
            const data = await response.json();
            
            const container = document.getElementById('active-alerts');
            
            if (data.alerts.length === 0) {
                container.innerHTML = '<div class="loading">No active alerts</div>';
                return;
            }
            
            container.innerHTML = data.alerts.map(alert => `
                <div class="alert-item ${alert.severity}">
                    <div class="alert-header">
                        <span class="alert-component">${alert.component}</span>
                        <span class="alert-severity ${alert.severity}">${alert.severity}</span>
                    </div>
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-time">
                        <small>${new Date(alert.timestamp * 1000).toLocaleString()}</small>
                    </div>
                </div>
            `).join('');
            
        } catch (error) {
            console.error('Failed to update alerts:', error);
        }
    }
    
    async updatePerformanceChart() {
        try {
            const duration = document.getElementById('history-duration')?.value || 60;
            const response = await fetch(`${this.baseUrl}/system/metrics?duration=${duration}`);
            const data = await response.json();
            
            this.renderPerformanceChart(data.metrics);
            
        } catch (error) {
            console.error('Failed to update performance chart:', error);
        }
    }
    
    renderPerformanceChart(metrics) {
        const canvas = document.getElementById('performance-canvas');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        if (metrics.length === 0) {
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No performance data available', width / 2, height / 2);
            return;
        }
        
        // Draw grid
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        
        // Horizontal grid lines
        for (let i = 0; i <= 10; i++) {
            const y = (height / 10) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
        
        // Vertical grid lines
        for (let i = 0; i <= 10; i++) {
            const x = (width / 10) * i;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
        
        // Draw performance lines
        this.drawMetricLine(ctx, metrics, 'cpu_usage', '#ff6b6b', width, height);
        this.drawMetricLine(ctx, metrics, 'memory_usage', '#4ecdc4', width, height);
        this.drawMetricLine(ctx, metrics, 'disk_usage', '#45b7d1', width, height);
        
        // Draw legend
        this.drawChartLegend(ctx, width, height);
    }
    
    drawMetricLine(ctx, metrics, metricName, color, width, height) {
        if (metrics.length < 2) return;
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        metrics.forEach((metric, index) => {
            const x = (index / (metrics.length - 1)) * width;
            const y = height - (metric[metricName] / 100) * height;
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
    }
    
    drawChartLegend(ctx, width, height) {
        const legends = [
            { color: '#ff6b6b', label: 'CPU' },
            { color: '#4ecdc4', label: 'Memory' },
            { color: '#45b7d1', label: 'Disk' }
        ];
        
        ctx.font = '12px Arial';
        ctx.textAlign = 'left';
        
        legends.forEach((legend, index) => {
            const x = 10;
            const y = 20 + (index * 20);
            
            // Draw color box
            ctx.fillStyle = legend.color;
            ctx.fillRect(x, y - 10, 15, 10);
            
            // Draw label
            ctx.fillStyle = '#333';
            ctx.fillText(legend.label, x + 20, y - 2);
        });
    }
    
    async updateSystemLogs() {
        try {
            const logType = document.getElementById('log-type')?.value || 'system';
            const lines = document.getElementById('log-lines')?.value || 100;
            
            const response = await fetch(`${this.baseUrl}/system/logs?type=${logType}&lines=${lines}`);
            const data = await response.json();
            
            const container = document.getElementById('system-logs');
            
            if (data.lines.length === 0) {
                container.textContent = 'No log entries found';
                return;
            }
            
            container.textContent = data.lines.join('');
            
            // Auto-scroll to bottom
            container.scrollTop = container.scrollHeight;
            
        } catch (error) {
            console.error('Failed to update system logs:', error);
        }
    }
}

// Initialize monitoring dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if monitoring panel exists
    if (document.getElementById('monitoring-panel')) {
        window.monitoringDashboard = new MonitoringDashboard();
    }
});