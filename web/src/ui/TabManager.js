/**
 * Tab Manager for Web Interface
 * 
 * Manages tab switching and panel visibility for the web application.
 */

class TabManager {
    constructor() {
        this.activeTab = 'video';
        this.tabs = new Map();
        this.panels = new Map();
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            this.initialize();
        }
    }
    
    initialize() {
        console.log('Initializing Tab Manager...');
        
        // Find all tab buttons and panels
        this.setupTabs();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Show initial tab
        this.showTab(this.activeTab);
    }
    
    setupTabs() {
        // Register tab buttons
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            const tabId = button.id.replace('-tab', '');
            this.tabs.set(tabId, button);
        });
        
        // Register panels
        const panels = document.querySelectorAll('.panel');
        panels.forEach(panel => {
            const panelId = panel.id.replace('-panel', '');
            this.panels.set(panelId, panel);
        });
        
        console.log(`Registered ${this.tabs.size} tabs and ${this.panels.size} panels`);
    }
    
    setupEventListeners() {
        this.tabs.forEach((button, tabId) => {
            button.addEventListener('click', () => {
                this.showTab(tabId);
            });
        });
    }
    
    showTab(tabId) {
        // Validate tab exists
        if (!this.tabs.has(tabId) || !this.panels.has(tabId)) {
            console.warn(`Tab or panel not found: ${tabId}`);
            return false;
        }
        
        // Remove active class from all tabs and panels
        this.tabs.forEach(button => button.classList.remove('active'));
        this.panels.forEach(panel => panel.classList.remove('active'));
        
        // Add active class to selected tab and panel
        const selectedTab = this.tabs.get(tabId);
        const selectedPanel = this.panels.get(tabId);
        
        selectedTab.classList.add('active');
        selectedPanel.classList.add('active');
        
        // Update active tab
        this.activeTab = tabId;
        
        // Trigger tab change event
        this.onTabChange(tabId);
        
        console.log(`Switched to tab: ${tabId}`);
        return true;
    }
    
    onTabChange(tabId) {
        // Handle tab-specific initialization or cleanup
        switch (tabId) {
            case 'video':
                this.onVideoTabActive();
                break;
            case 'live':
                this.onLiveTabActive();
                break;
            case 'hardware':
                this.onHardwareTabActive();
                break;
        }
        
        // Dispatch custom event
        const event = new CustomEvent('tabChanged', {
            detail: { tabId, previousTab: this.activeTab }
        });
        document.dispatchEvent(event);
    }
    
    onVideoTabActive() {
        // Video tab specific initialization
        console.log('Video tab activated');
    }
    
    onLiveTabActive() {
        // Live feed tab specific initialization
        console.log('Live feed tab activated');
        
        // Refresh camera list if live feed viewer is available
        if (typeof liveFeedViewer !== 'undefined' && liveFeedViewer) {
            liveFeedViewer.refreshCameraList();
        }
    }
    
    onHardwareTabActive() {
        // Hardware tab specific initialization
        console.log('Hardware tab activated');
        
        // Refresh device list if hardware interface is available
        if (typeof hardwareInterface !== 'undefined' && hardwareInterface) {
            hardwareInterface.refreshDeviceList();
        }
    }
    
    getActiveTab() {
        return this.activeTab;
    }
    
    isTabActive(tabId) {
        return this.activeTab === tabId;
    }
    
    getAvailableTabs() {
        return Array.from(this.tabs.keys());
    }
}

// Create global instance
const tabManager = new TabManager();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TabManager;
}