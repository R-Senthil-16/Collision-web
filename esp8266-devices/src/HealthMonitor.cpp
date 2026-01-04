#include "HealthMonitor.h"
#include "config.h"

HealthMonitor::HealthMonitor(String deviceId) {
    this->deviceId = deviceId;
    this->raspberryPiIP = "";
    this->alertCount = 0;
    
    // Initialize timing
    lastMetricsUpdate = 0;
    lastStatusReport = 0;
    lastHeartbeat = 0;
    
    // Set default thresholds
    minFreeHeap = 8192;  // 8KB minimum free heap
    minWifiRSSI = -80;   // -80 dBm minimum signal strength
    maxTemperature = 70.0; // 70°C maximum temperature
    maxLoopTime = 100;   // 100ms maximum loop time
    
    // Initialize metrics
    memset(&currentMetrics, 0, sizeof(HealthMetrics));
    currentMetrics.overallHealth = HEALTH_GOOD;
    currentMetrics.healthMessage = "System starting up";
    
    // Initialize alerts array
    for (int i = 0; i < 10; i++) {
        alerts[i].alertId = "";
        alerts[i].acknowledged = true;
    }
}

void HealthMonitor::begin() {
    DEBUG_PRINTLN("Initializing Health Monitor...");
    
    // Initialize metrics
    updateMetrics();
    
    DEBUG_PRINTLN("Health Monitor initialization complete");
}

void HealthMonitor::setRaspberryPiIP(String ip) {
    raspberryPiIP = ip;
    DEBUG_PRINTF("Raspberry Pi IP set to: %s\n", ip.c_str());
}

void HealthMonitor::setThresholds(uint32_t minHeap, int minRSSI, float maxTemp, unsigned long maxLoop) {
    minFreeHeap = minHeap;
    minWifiRSSI = minRSSI;
    maxTemperature = maxTemp;
    maxLoopTime = maxLoop;
    
    DEBUG_PRINTF("Health thresholds updated: Heap=%d, RSSI=%d, Temp=%.1f, Loop=%lu\n",
                 minHeap, minRSSI, maxTemp, maxLoop);
}

void HealthMonitor::updateMetrics() {
    unsigned long currentTime = millis();
    
    if (currentTime - lastMetricsUpdate >= 1000) { // Update every second
        updateSystemMetrics();
        updateNetworkMetrics();
        updateHardwareMetrics();
        updatePerformanceMetrics();
        evaluateOverallHealth();
        checkThresholds();
        
        lastMetricsUpdate = currentTime;
    }
}

void HealthMonitor::updateSystemMetrics() {
    currentMetrics.freeHeap = ESP.getFreeHeap();
    currentMetrics.maxFreeBlockSize = ESP.getMaxFreeBlockSize();
    currentMetrics.heapFragmentation = ESP.getHeapFragmentation();
    currentMetrics.uptime = millis();
    
    // Simple CPU usage estimation based on loop timing
    static unsigned long lastCpuCheck = 0;
    static unsigned long busyTime = 0;
    
    unsigned long now = millis();
    if (now - lastCpuCheck >= 1000) {
        currentMetrics.cpuUsage = (float)busyTime / 1000.0 * 100.0;
        busyTime = 0;
        lastCpuCheck = now;
    }
}

void HealthMonitor::updateNetworkMetrics() {
    currentMetrics.wifiConnected = (WiFi.status() == WL_CONNECTED);
    
    if (currentMetrics.wifiConnected) {
        currentMetrics.wifiRSSI = WiFi.RSSI();
        currentMetrics.wifiSSID = WiFi.SSID();
        currentMetrics.ipAddress = WiFi.localIP();
    } else {
        currentMetrics.wifiRSSI = 0;
        currentMetrics.wifiSSID = "";
        currentMetrics.ipAddress = IPAddress(0, 0, 0, 0);
        currentMetrics.lastNetworkError = millis();
        currentMetrics.networkErrorCount++;
    }
}

void HealthMonitor::updateHardwareMetrics() {
    currentMetrics.temperature = readTemperature();
    currentMetrics.voltage = readVoltage();
    
    // Check hardware component status
    // This would be expanded based on actual hardware connected
    currentMetrics.hardwareStatus[0] = true; // LED system
    currentMetrics.hardwareStatus[1] = true; // Servo
    currentMetrics.hardwareStatus[2] = true; // Relay
    currentMetrics.hardwareStatus[3] = true; // Buzzer
    currentMetrics.hardwareStatus[4] = currentMetrics.wifiConnected; // WiFi
    currentMetrics.hardwareStatus[5] = true; // Status LED
    currentMetrics.hardwareStatus[6] = true; // Button
    currentMetrics.hardwareStatus[7] = true; // Reserved
}

void HealthMonitor::updatePerformanceMetrics() {
    // Performance metrics are updated via logPerformance() method
    // This method just maintains the data
}

void HealthMonitor::evaluateOverallHealth() {
    HealthStatus worstStatus = HEALTH_EXCELLENT;
    String healthMsg = "All systems operational";
    
    // Check memory health
    if (currentMetrics.freeHeap < minFreeHeap / 2) {
        worstStatus = HEALTH_CRITICAL;
        healthMsg = "Critical memory shortage";
    } else if (currentMetrics.freeHeap < minFreeHeap) {
        worstStatus = max(worstStatus, HEALTH_WARNING);
        healthMsg = "Low memory warning";
    }
    
    // Check network health
    if (!currentMetrics.wifiConnected) {
        worstStatus = max(worstStatus, HEALTH_CRITICAL);
        healthMsg = "Network disconnected";
    } else if (currentMetrics.wifiRSSI < minWifiRSSI) {
        worstStatus = max(worstStatus, HEALTH_WARNING);
        healthMsg = "Weak WiFi signal";
    }
    
    // Check temperature
    if (currentMetrics.temperature > maxTemperature) {
        worstStatus = max(worstStatus, HEALTH_CRITICAL);
        healthMsg = "Temperature critical";
    } else if (currentMetrics.temperature > maxTemperature * 0.9) {
        worstStatus = max(worstStatus, HEALTH_WARNING);
        healthMsg = "Temperature elevated";
    }
    
    // Check performance
    if (currentMetrics.maxLoopTime > maxLoopTime * 2) {
        worstStatus = max(worstStatus, HEALTH_WARNING);
        healthMsg = "Performance degraded";
    }
    
    currentMetrics.overallHealth = worstStatus;
    currentMetrics.healthMessage = healthMsg;
    currentMetrics.lastHealthUpdate = millis();
}

void HealthMonitor::checkThresholds() {
    // Check for threshold violations and raise alerts
    
    if (currentMetrics.freeHeap < minFreeHeap && currentMetrics.freeHeap > 0) {
        raiseAlert(HEALTH_WARNING, "Memory", "Free heap below threshold: " + String(currentMetrics.freeHeap));
    }
    
    if (currentMetrics.wifiRSSI < minWifiRSSI && currentMetrics.wifiConnected) {
        raiseAlert(HEALTH_WARNING, "Network", "WiFi signal weak: " + String(currentMetrics.wifiRSSI) + " dBm");
    }
    
    if (currentMetrics.temperature > maxTemperature) {
        raiseAlert(HEALTH_CRITICAL, "Hardware", "Temperature critical: " + String(currentMetrics.temperature) + "°C");
    }
    
    if (currentMetrics.maxLoopTime > maxLoopTime) {
        raiseAlert(HEALTH_WARNING, "Performance", "Loop time exceeded: " + String(currentMetrics.maxLoopTime) + "ms");
    }
}

void HealthMonitor::addAlert(HealthStatus severity, String component, String message) {
    // Find an empty slot or replace oldest alert
    int slot = -1;
    unsigned long oldestTime = ULONG_MAX;
    
    for (int i = 0; i < 10; i++) {
        if (alerts[i].alertId.length() == 0 || alerts[i].acknowledged) {
            slot = i;
            break;
        }
        if (alerts[i].timestamp < oldestTime) {
            oldestTime = alerts[i].timestamp;
            slot = i;
        }
    }
    
    if (slot >= 0) {
        alerts[slot].alertId = deviceId + "_" + String(millis());
        alerts[slot].severity = severity;
        alerts[slot].component = component;
        alerts[slot].message = message;
        alerts[slot].timestamp = millis();
        alerts[slot].acknowledged = false;
        
        if (slot >= alertCount) {
            alertCount = slot + 1;
        }
        
        DEBUG_PRINTF("Alert raised: %s - %s\n", component.c_str(), message.c_str());
        
        // Send alert to Raspberry Pi
        sendAlertToRaspberryPi(alerts[slot]);
    }
}

void HealthMonitor::clearOldAlerts() {
    unsigned long currentTime = millis();
    
    for (int i = 0; i < alertCount; i++) {
        // Clear alerts older than 1 hour or acknowledged alerts older than 5 minutes
        if ((currentTime - alerts[i].timestamp > 3600000) ||
            (alerts[i].acknowledged && currentTime - alerts[i].timestamp > 300000)) {
            alerts[i].alertId = "";
            alerts[i].acknowledged = true;
        }
    }
}

float HealthMonitor::readTemperature() {
    // ESP8266 doesn't have built-in temperature sensor
    // This would read from an external sensor like DS18B20
    // For now, simulate temperature based on system load
    float baseTemp = 25.0;
    float loadFactor = (100.0 - currentMetrics.cpuUsage) / 100.0;
    return baseTemp + (10.0 * (1.0 - loadFactor));
}

float HealthMonitor::readVoltage() {
    // Read supply voltage (ESP8266 ADC can measure VCC with special configuration)
    // For now, return a simulated value
    return 3.3 + (random(-10, 10) / 100.0);
}

void HealthMonitor::reportStatus() {
    unsigned long currentTime = millis();
    
    if (currentTime - lastStatusReport >= 30000) { // Report every 30 seconds
        if (sendStatusToRaspberryPi()) {
            DEBUG_PRINTLN("Status report sent successfully");
        } else {
            DEBUG_PRINTLN("Failed to send status report");
        }
        
        lastStatusReport = currentTime;
    }
}

void HealthMonitor::sendHeartbeat() {
    unsigned long currentTime = millis();
    
    if (currentTime - lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
        // Create heartbeat with basic health info
        DynamicJsonDocument doc(JSON_BUFFER_SIZE);
        doc["type"] = "heartbeat";
        doc["device_id"] = deviceId;
        doc["timestamp"] = currentTime;
        doc["health_status"] = currentMetrics.overallHealth;
        doc["uptime"] = currentMetrics.uptime;
        doc["free_heap"] = currentMetrics.freeHeap;
        doc["wifi_rssi"] = currentMetrics.wifiRSSI;
        
        String heartbeatJson;
        serializeJson(doc, heartbeatJson);
        
        DEBUG_PRINTF("Heartbeat: %s\n", heartbeatJson.c_str());
        
        // TODO: Send to Raspberry Pi
        lastHeartbeat = currentTime;
    }
}

void HealthMonitor::logPerformance(unsigned long loopTime, unsigned long commandTime, int queueSize) {
    currentMetrics.loopTime = loopTime;
    currentMetrics.commandProcessingTime = commandTime;
    currentMetrics.commandQueueSize = queueSize;
    
    if (loopTime > currentMetrics.maxLoopTime) {
        currentMetrics.maxLoopTime = loopTime;
    }
}

HealthStatus HealthMonitor::getOverallHealth() {
    return currentMetrics.overallHealth;
}

String HealthMonitor::getHealthMessage() {
    return currentMetrics.healthMessage;
}

HealthMetrics HealthMonitor::getMetrics() {
    return currentMetrics;
}

void HealthMonitor::raiseAlert(HealthStatus severity, String component, String message) {
    addAlert(severity, component, message);
}

void HealthMonitor::acknowledgeAlert(String alertId) {
    for (int i = 0; i < alertCount; i++) {
        if (alerts[i].alertId == alertId) {
            alerts[i].acknowledged = true;
            DEBUG_PRINTF("Alert acknowledged: %s\n", alertId.c_str());
            break;
        }
    }
}

int HealthMonitor::getActiveAlertCount() {
    int count = 0;
    for (int i = 0; i < alertCount; i++) {
        if (!alerts[i].acknowledged && alerts[i].alertId.length() > 0) {
            count++;
        }
    }
    return count;
}

HealthAlert* HealthMonitor::getAlerts() {
    return alerts;
}

String HealthMonitor::getStatusJson() {
    DynamicJsonDocument doc(JSON_BUFFER_SIZE * 2); // Larger buffer for complete status
    
    doc["device_id"] = deviceId;
    doc["timestamp"] = millis();
    doc["health_status"] = currentMetrics.overallHealth;
    doc["health_message"] = currentMetrics.healthMessage;
    
    // System metrics
    JsonObject system = doc.createNestedObject("system");
    system["free_heap"] = currentMetrics.freeHeap;
    system["max_free_block"] = currentMetrics.maxFreeBlockSize;
    system["heap_fragmentation"] = currentMetrics.heapFragmentation;
    system["uptime"] = currentMetrics.uptime;
    system["cpu_usage"] = currentMetrics.cpuUsage;
    
    // Network metrics
    JsonObject network = doc.createNestedObject("network");
    network["wifi_connected"] = currentMetrics.wifiConnected;
    network["wifi_rssi"] = currentMetrics.wifiRSSI;
    network["wifi_ssid"] = currentMetrics.wifiSSID;
    network["ip_address"] = currentMetrics.ipAddress.toString();
    network["error_count"] = currentMetrics.networkErrorCount;
    
    // Hardware metrics
    JsonObject hardware = doc.createNestedObject("hardware");
    hardware["temperature"] = currentMetrics.temperature;
    hardware["voltage"] = currentMetrics.voltage;
    JsonArray hwStatus = hardware.createNestedArray("component_status");
    for (int i = 0; i < 8; i++) {
        hwStatus.add(currentMetrics.hardwareStatus[i]);
    }
    
    // Performance metrics
    JsonObject performance = doc.createNestedObject("performance");
    performance["loop_time"] = currentMetrics.loopTime;
    performance["max_loop_time"] = currentMetrics.maxLoopTime;
    performance["command_processing_time"] = currentMetrics.commandProcessingTime;
    performance["command_queue_size"] = currentMetrics.commandQueueSize;
    
    // Active alerts
    JsonArray alertsArray = doc.createNestedArray("alerts");
    for (int i = 0; i < alertCount; i++) {
        if (!alerts[i].acknowledged && alerts[i].alertId.length() > 0) {
            JsonObject alert = alertsArray.createNestedObject();
            alert["id"] = alerts[i].alertId;
            alert["severity"] = alerts[i].severity;
            alert["component"] = alerts[i].component;
            alert["message"] = alerts[i].message;
            alert["timestamp"] = alerts[i].timestamp;
        }
    }
    
    String statusJson;
    serializeJson(doc, statusJson);
    
    return statusJson;
}

String HealthMonitor::getHealthReportJson() {
    return getStatusJson(); // For now, same as status
}

bool HealthMonitor::sendStatusToRaspberryPi() {
    if (raspberryPiIP.length() == 0 || !currentMetrics.wifiConnected) {
        return false;
    }
    
    WiFiClient client;
    HTTPClient http;
    
    String url = "http://" + raspberryPiIP + ":5000/api/device/status";
    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");
    
    String statusJson = getStatusJson();
    int httpResponseCode = http.POST(statusJson);
    
    bool success = (httpResponseCode == 200);
    
    if (!success) {
        DEBUG_PRINTF("Failed to send status: HTTP %d\n", httpResponseCode);
        currentMetrics.lastNetworkError = millis();
        currentMetrics.networkErrorCount++;
    }
    
    http.end();
    return success;
}

bool HealthMonitor::sendAlertToRaspberryPi(const HealthAlert& alert) {
    if (raspberryPiIP.length() == 0 || !currentMetrics.wifiConnected) {
        return false;
    }
    
    WiFiClient client;
    HTTPClient http;
    
    String url = "http://" + raspberryPiIP + ":5000/api/device/alert";
    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");
    
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    doc["device_id"] = deviceId;
    doc["alert_id"] = alert.alertId;
    doc["severity"] = alert.severity;
    doc["component"] = alert.component;
    doc["message"] = alert.message;
    doc["timestamp"] = alert.timestamp;
    
    String alertJson;
    serializeJson(doc, alertJson);
    
    int httpResponseCode = http.POST(alertJson);
    bool success = (httpResponseCode == 200);
    
    if (!success) {
        DEBUG_PRINTF("Failed to send alert: HTTP %d\n", httpResponseCode);
    }
    
    http.end();
    return success;
}

void HealthMonitor::monitorEnvironment() {
    // Monitor environmental conditions
    updateHardwareMetrics();
    
    // Check for environmental alerts
    if (currentMetrics.temperature > maxTemperature * 0.8) {
        raiseAlert(HEALTH_WARNING, "Environment", "Temperature rising: " + String(currentMetrics.temperature) + "°C");
    }
    
    if (currentMetrics.voltage < 3.0) {
        raiseAlert(HEALTH_WARNING, "Power", "Low voltage detected: " + String(currentMetrics.voltage) + "V");
    }
}

void HealthMonitor::checkHardwareHealth() {
    // Check hardware component health
    for (int i = 0; i < 8; i++) {
        if (!currentMetrics.hardwareStatus[i]) {
            String component = "Component_" + String(i);
            raiseAlert(HEALTH_WARNING, "Hardware", component + " failure detected");
        }
    }
}

void HealthMonitor::validateNetworkHealth() {
    if (!currentMetrics.wifiConnected) {
        raiseAlert(HEALTH_CRITICAL, "Network", "WiFi connection lost");
    } else if (currentMetrics.wifiRSSI < minWifiRSSI) {
        raiseAlert(HEALTH_WARNING, "Network", "WiFi signal strength low: " + String(currentMetrics.wifiRSSI) + " dBm");
    }
}

void HealthMonitor::performDiagnostics() {
    DEBUG_PRINTLN("Performing system diagnostics...");
    
    // Test memory
    uint32_t testHeap = ESP.getFreeHeap();
    DEBUG_PRINTF("Free heap: %d bytes\n", testHeap);
    
    // Test network
    if (WiFi.status() == WL_CONNECTED) {
        DEBUG_PRINTF("WiFi connected: %s (RSSI: %d dBm)\n", WiFi.SSID().c_str(), WiFi.RSSI());
    } else {
        DEBUG_PRINTLN("WiFi not connected");
    }
    
    // Test hardware components
    DEBUG_PRINTLN("Hardware component status:");
    const char* componentNames[] = {"LED", "Servo", "Relay", "Buzzer", "WiFi", "Status LED", "Button", "Reserved"};
    for (int i = 0; i < 8; i++) {
        DEBUG_PRINTF("  %s: %s\n", componentNames[i], currentMetrics.hardwareStatus[i] ? "OK" : "FAIL");
    }
    
    DEBUG_PRINTLN("Diagnostics complete");
}

void HealthMonitor::runSelfTest() {
    DEBUG_PRINTLN("Running self-test...");
    
    // Test basic functionality
    performDiagnostics();
    
    // Test alert system
    raiseAlert(HEALTH_GOOD, "SelfTest", "Self-test alert - system operational");
    
    DEBUG_PRINTLN("Self-test complete");
}

String HealthMonitor::getDiagnosticReport() {
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    
    doc["device_id"] = deviceId;
    doc["diagnostic_timestamp"] = millis();
    doc["overall_health"] = currentMetrics.overallHealth;
    doc["health_message"] = currentMetrics.healthMessage;
    doc["uptime"] = currentMetrics.uptime;
    doc["free_heap"] = currentMetrics.freeHeap;
    doc["wifi_connected"] = currentMetrics.wifiConnected;
    doc["wifi_rssi"] = currentMetrics.wifiRSSI;
    doc["temperature"] = currentMetrics.temperature;
    doc["voltage"] = currentMetrics.voltage;
    doc["active_alerts"] = getActiveAlertCount();
    
    String report;
    serializeJson(doc, report);
    
    return report;
}

void HealthMonitor::update() {
    updateMetrics();
    reportStatus();
    sendHeartbeat();
    clearOldAlerts();
    monitorEnvironment();
    checkHardwareHealth();
    validateNetworkHealth();
}