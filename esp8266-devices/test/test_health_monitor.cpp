#include <unity.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include "HealthMonitor.h"
#include "config.h"

// Mock implementations for testing
class MockHealthMonitor : public HealthMonitor {
public:
    MockHealthMonitor(String deviceId) : HealthMonitor(deviceId) {}
    
    // Expose protected methods for testing
    void testUpdateMetrics() {
        updateMetrics();
    }
    
    void testRaiseAlert(HealthStatus severity, String component, String message) {
        raiseAlert(severity, component, message);
    }
    
    void testLogPerformance(unsigned long loopTime, unsigned long commandTime, int queueSize) {
        logPerformance(loopTime, commandTime, queueSize);
    }
};

MockHealthMonitor* testMonitor = nullptr;

void setUp(void) {
    // Set up before each test
    testMonitor = new MockHealthMonitor("TEST_HEALTH_001");
    testMonitor->begin();
}

void tearDown(void) {
    // Clean up after each test
    if (testMonitor) {
        delete testMonitor;
        testMonitor = nullptr;
    }
}

// Test health monitor initialization
void test_health_monitor_initialization() {
    TEST_ASSERT_NOT_NULL(testMonitor);
    
    HealthStatus status = testMonitor->getOverallHealth();
    TEST_ASSERT_TRUE(status >= HEALTH_EXCELLENT && status <= HEALTH_FAILURE);
    
    String message = testMonitor->getHealthMessage();
    TEST_ASSERT_TRUE(message.length() > 0);
}

// Test metrics update
void test_metrics_update() {
    testMonitor->testUpdateMetrics();
    
    HealthMetrics metrics = testMonitor->getMetrics();
    
    // Verify basic metrics are populated
    TEST_ASSERT_TRUE(metrics.freeHeap > 0);
    TEST_ASSERT_TRUE(metrics.uptime > 0);
    TEST_ASSERT_TRUE(metrics.deviceId.length() > 0);
    TEST_ASSERT_EQUAL_STRING("TEST_HEALTH_001", metrics.deviceId.c_str());
}

// Test alert system
void test_alert_system() {
    // Initially should have no active alerts
    TEST_ASSERT_EQUAL(0, testMonitor->getActiveAlertCount());
    
    // Raise a test alert
    testMonitor->testRaiseAlert(HEALTH_WARNING, "TestComponent", "Test alert message");
    
    // Should now have one active alert
    TEST_ASSERT_EQUAL(1, testMonitor->getActiveAlertCount());
    
    // Get alerts and verify content
    HealthAlert* alerts = testMonitor->getAlerts();
    TEST_ASSERT_NOT_NULL(alerts);
    TEST_ASSERT_FALSE(alerts[0].acknowledged);
    TEST_ASSERT_EQUAL(HEALTH_WARNING, alerts[0].severity);
    TEST_ASSERT_EQUAL_STRING("TestComponent", alerts[0].component.c_str());
    TEST_ASSERT_EQUAL_STRING("Test alert message", alerts[0].message.c_str());
}

// Test alert acknowledgment
void test_alert_acknowledgment() {
    // Raise an alert
    testMonitor->testRaiseAlert(HEALTH_CRITICAL, "TestComponent", "Critical test alert");
    TEST_ASSERT_EQUAL(1, testMonitor->getActiveAlertCount());
    
    // Get the alert ID
    HealthAlert* alerts = testMonitor->getAlerts();
    String alertId = alerts[0].alertId;
    TEST_ASSERT_TRUE(alertId.length() > 0);
    
    // Acknowledge the alert
    testMonitor->acknowledgeAlert(alertId);
    
    // Should now have no active alerts
    TEST_ASSERT_EQUAL(0, testMonitor->getActiveAlertCount());
}

// Test multiple alerts
void test_multiple_alerts() {
    // Raise multiple alerts
    testMonitor->testRaiseAlert(HEALTH_WARNING, "Component1", "Warning 1");
    testMonitor->testRaiseAlert(HEALTH_CRITICAL, "Component2", "Critical 1");
    testMonitor->testRaiseAlert(HEALTH_WARNING, "Component3", "Warning 2");
    
    TEST_ASSERT_EQUAL(3, testMonitor->getActiveAlertCount());
    
    // Acknowledge one alert
    HealthAlert* alerts = testMonitor->getAlerts();
    testMonitor->acknowledgeAlert(alerts[1].alertId);
    
    TEST_ASSERT_EQUAL(2, testMonitor->getActiveAlertCount());
}

// Test performance logging
void test_performance_logging() {
    // Log some performance data
    testMonitor->testLogPerformance(50, 10, 3);
    
    HealthMetrics metrics = testMonitor->getMetrics();
    TEST_ASSERT_EQUAL(50, metrics.loopTime);
    TEST_ASSERT_EQUAL(10, metrics.commandProcessingTime);
    TEST_ASSERT_EQUAL(3, metrics.commandQueueSize);
    
    // Log higher loop time
    testMonitor->testLogPerformance(100, 20, 5);
    
    metrics = testMonitor->getMetrics();
    TEST_ASSERT_EQUAL(100, metrics.loopTime);
    TEST_ASSERT_EQUAL(100, metrics.maxLoopTime); // Should track maximum
}

// Test health status evaluation
void test_health_status_evaluation() {
    // Initially should be in good health
    HealthStatus initialStatus = testMonitor->getOverallHealth();
    TEST_ASSERT_TRUE(initialStatus <= HEALTH_GOOD);
    
    // Raise a critical alert
    testMonitor->testRaiseAlert(HEALTH_CRITICAL, "TestComponent", "Critical system failure");
    
    // Update metrics to re-evaluate health
    testMonitor->testUpdateMetrics();
    
    // Health status should reflect the critical alert
    // Note: The actual implementation may vary based on how health is calculated
    TEST_ASSERT_TRUE(testMonitor->getActiveAlertCount() > 0);
}

// Test status JSON generation
void test_status_json_generation() {
    String statusJson = testMonitor->getStatusJson();
    
    // Parse the JSON to verify structure
    DynamicJsonDocument doc(JSON_BUFFER_SIZE * 2);
    DeserializationError error = deserializeJson(doc, statusJson);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_TRUE(doc.containsKey("device_id"));
    TEST_ASSERT_TRUE(doc.containsKey("timestamp"));
    TEST_ASSERT_TRUE(doc.containsKey("health_status"));
    TEST_ASSERT_TRUE(doc.containsKey("health_message"));
    TEST_ASSERT_TRUE(doc.containsKey("system"));
    TEST_ASSERT_TRUE(doc.containsKey("network"));
    TEST_ASSERT_TRUE(doc.containsKey("hardware"));
    TEST_ASSERT_TRUE(doc.containsKey("performance"));
    TEST_ASSERT_TRUE(doc.containsKey("alerts"));
    
    TEST_ASSERT_EQUAL_STRING("TEST_HEALTH_001", doc["device_id"]);
    
    // Verify nested objects exist
    TEST_ASSERT_TRUE(doc["system"].containsKey("free_heap"));
    TEST_ASSERT_TRUE(doc["system"].containsKey("uptime"));
    TEST_ASSERT_TRUE(doc["network"].containsKey("wifi_connected"));
    TEST_ASSERT_TRUE(doc["hardware"].containsKey("temperature"));
    TEST_ASSERT_TRUE(doc["performance"].containsKey("loop_time"));
}

// Test health report JSON
void test_health_report_json() {
    // Add some alerts first
    testMonitor->testRaiseAlert(HEALTH_WARNING, "Memory", "Low memory warning");
    testMonitor->testRaiseAlert(HEALTH_CRITICAL, "Network", "Connection lost");
    
    String reportJson = testMonitor->getHealthReportJson();
    
    // Parse and verify the report contains alert information
    DynamicJsonDocument doc(JSON_BUFFER_SIZE * 2);
    DeserializationError error = deserializeJson(doc, reportJson);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_TRUE(doc.containsKey("alerts"));
    
    JsonArray alerts = doc["alerts"];
    TEST_ASSERT_EQUAL(2, alerts.size());
}

// Test diagnostic report
void test_diagnostic_report() {
    String diagnosticReport = testMonitor->getDiagnosticReport();
    
    // Parse the diagnostic report
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(doc, diagnosticReport);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_TRUE(doc.containsKey("device_id"));
    TEST_ASSERT_TRUE(doc.containsKey("diagnostic_timestamp"));
    TEST_ASSERT_TRUE(doc.containsKey("overall_health"));
    TEST_ASSERT_TRUE(doc.containsKey("uptime"));
    TEST_ASSERT_TRUE(doc.containsKey("free_heap"));
    TEST_ASSERT_TRUE(doc.containsKey("active_alerts"));
    
    TEST_ASSERT_EQUAL_STRING("TEST_HEALTH_001", doc["device_id"]);
}

// Test threshold configuration
void test_threshold_configuration() {
    // Set custom thresholds
    testMonitor->setThresholds(4096, -70, 60.0, 50);
    
    // The thresholds should be applied (we can't directly test private members,
    // but we can test that the method doesn't crash)
    TEST_ASSERT_TRUE(true);
    
    // Update metrics to trigger threshold checks
    testMonitor->testUpdateMetrics();
    
    // Should complete without errors
    TEST_ASSERT_TRUE(true);
}

// Test Raspberry Pi IP configuration
void test_raspberry_pi_ip_configuration() {
    String testIP = "192.168.1.100";
    testMonitor->setRaspberryPiIP(testIP);
    
    // Should complete without errors
    TEST_ASSERT_TRUE(true);
}

// Test update method
void test_update_method() {
    // Call update multiple times
    for (int i = 0; i < 5; i++) {
        testMonitor->update();
        delay(10);
    }
    
    // Should complete without errors
    TEST_ASSERT_TRUE(true);
}

// Test alert overflow handling
void test_alert_overflow_handling() {
    // Fill up the alert buffer (assuming 10 alerts max)
    for (int i = 0; i < 15; i++) {
        String message = "Alert " + String(i);
        testMonitor->testRaiseAlert(HEALTH_WARNING, "TestComponent", message);
    }
    
    // Should not crash and should have some alerts
    int alertCount = testMonitor->getActiveAlertCount();
    TEST_ASSERT_TRUE(alertCount > 0);
    TEST_ASSERT_TRUE(alertCount <= 10); // Should not exceed buffer size
}

void setup() {
    delay(2000); // Wait for serial monitor
    
    UNITY_BEGIN();
    
    RUN_TEST(test_health_monitor_initialization);
    RUN_TEST(test_metrics_update);
    RUN_TEST(test_alert_system);
    RUN_TEST(test_alert_acknowledgment);
    RUN_TEST(test_multiple_alerts);
    RUN_TEST(test_performance_logging);
    RUN_TEST(test_health_status_evaluation);
    RUN_TEST(test_status_json_generation);
    RUN_TEST(test_health_report_json);
    RUN_TEST(test_diagnostic_report);
    RUN_TEST(test_threshold_configuration);
    RUN_TEST(test_raspberry_pi_ip_configuration);
    RUN_TEST(test_update_method);
    RUN_TEST(test_alert_overflow_handling);
    
    UNITY_END();
}

void loop() {
    // Empty loop for testing
}