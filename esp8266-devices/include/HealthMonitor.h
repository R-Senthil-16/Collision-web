#ifndef HEALTH_MONITOR_H
#define HEALTH_MONITOR_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

// Health status levels
enum HealthStatus {
    HEALTH_EXCELLENT = 0,
    HEALTH_GOOD = 1,
    HEALTH_WARNING = 2,
    HEALTH_CRITICAL = 3,
    HEALTH_FAILURE = 4
};

// Health metrics structure
struct HealthMetrics {
    // System metrics
    uint32_t freeHeap;
    uint32_t maxFreeBlockSize;
    uint8_t heapFragmentation;
    unsigned long uptime;
    float cpuUsage;
    
    // Network metrics
    bool wifiConnected;
    int wifiRSSI;
    String wifiSSID;
    IPAddress ipAddress;
    unsigned long lastNetworkError;
    int networkErrorCount;
    
    // Hardware metrics
    float temperature;
    float voltage;
    bool hardwareStatus[8]; // Various hardware components
    unsigned long lastHardwareError;
    int hardwareErrorCount;
    
    // Performance metrics
    unsigned long loopTime;
    unsigned long maxLoopTime;
    unsigned long commandProcessingTime;
    int commandQueueSize;
    
    // Overall health
    HealthStatus overallHealth;
    String healthMessage;
    unsigned long lastHealthUpdate;
};

// Alert structure
struct HealthAlert {
    String alertId;
    HealthStatus severity;
    String component;
    String message;
    unsigned long timestamp;
    bool acknowledged;
};

class HealthMonitor {
private:
    String deviceId;
    String raspberryPiIP;
    HealthMetrics currentMetrics;
    HealthAlert alerts[10]; // Alert buffer
    int alertCount;
    
    // Monitoring intervals
    unsigned long lastMetricsUpdate;
    unsigned long lastStatusReport;
    unsigned long lastHeartbeat;
    
    // Thresholds
    uint32_t minFreeHeap;
    int minWifiRSSI;
    float maxTemperature;
    unsigned long maxLoopTime;
    
    // Private methods
    void updateSystemMetrics();
    void updateNetworkMetrics();
    void updateHardwareMetrics();
    void updatePerformanceMetrics();
    void evaluateOverallHealth();
    void checkThresholds();
    void addAlert(HealthStatus severity, String component, String message);
    void clearOldAlerts();
    float readTemperature();
    float readVoltage();
    
public:
    HealthMonitor(String deviceId);
    
    // Initialization
    void begin();
    void setRaspberryPiIP(String ip);
    void setThresholds(uint32_t minHeap, int minRSSI, float maxTemp, unsigned long maxLoop);
    
    // Monitoring methods
    void updateMetrics();
    void reportStatus();
    void sendHeartbeat();
    void logPerformance(unsigned long loopTime, unsigned long commandTime, int queueSize);
    
    // Health assessment
    HealthStatus getOverallHealth();
    String getHealthMessage();
    HealthMetrics getMetrics();
    
    // Alert management
    void raiseAlert(HealthStatus severity, String component, String message);
    void acknowledgeAlert(String alertId);
    int getActiveAlertCount();
    HealthAlert* getAlerts();
    
    // Status reporting
    String getStatusJson();
    String getHealthReportJson();
    bool sendStatusToRaspberryPi();
    bool sendAlertToRaspberryPi(const HealthAlert& alert);
    
    // Environmental monitoring
    void monitorEnvironment();
    void checkHardwareHealth();
    void validateNetworkHealth();
    
    // Diagnostic methods
    void performDiagnostics();
    void runSelfTest();
    String getDiagnosticReport();
    
    // Main update method
    void update();
};

#endif // HEALTH_MONITOR_H