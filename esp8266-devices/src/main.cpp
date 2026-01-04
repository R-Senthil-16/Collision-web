/*
 * Main ESP8266 Device Controller
 * Collision Detection System - ESP8266 Firmware
 */

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <ArduinoJson.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include "config.h"
#include "DeviceController.h"
#include "HealthMonitor.h"

// Global variables
String deviceId;
String deviceMAC;
ESP8266WebServer server(SERVER_PORT);
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 0, 60000);
unsigned long lastHeartbeat = 0;
unsigned long lastStatusUpdate = 0;
bool wifiConnected = false;
int wifiReconnectAttempts = 0;

// WiFi credentials (will be set via configuration)
String wifiSSID = "";
String wifiPassword = "";
String raspberryPiIP = "";

// Device controller and health monitor instances
DeviceController* deviceController = nullptr;
HealthMonitor* healthMonitor = nullptr;

// Function declarations
void setupWiFi();
void setupDeviceIdentification();
void setupWebServer();
void setupOTA();
void connectToWiFi();
void handleWiFiReconnection();
void sendHeartbeat();
void updateStatus();
String generateDeviceId();
void handleRoot();
void handleStatus();
void handleConfig();
void handleHealth();
void handleDiagnostics();
void handleAlerts();

void setup() {
    Serial.begin(115200);
    delay(1000);
    
    DEBUG_PRINTLN("=================================");
    DEBUG_PRINTLN("ESP8266 Collision Detection Device");
    DEBUG_PRINTLN("Firmware Version: " FIRMWARE_VERSION);
    DEBUG_PRINTLN("=================================");
    
    // Setup device identification
    setupDeviceIdentification();
    
    // Initialize device controller
    deviceController = new DeviceController(deviceId);
    deviceController->begin();
    
    // Initialize health monitor
    healthMonitor = new HealthMonitor(deviceId);
    healthMonitor->begin();
    
    // Setup WiFi connection
    setupWiFi();
    
    // Setup web server
    setupWebServer();
    
    // Setup OTA updates
    setupOTA();
    
    // Initialize NTP client
    timeClient.begin();
    
    DEBUG_PRINTLN("Device initialization complete");
    DEBUG_PRINTF("Device ID: %s\n", deviceId.c_str());
    DEBUG_PRINTF("MAC Address: %s\n", deviceMAC.c_str());
    
    // Perform hardware self-test
    deviceController->setupHardware();
    
    // Blink status LED to indicate ready state
    for(int i = 0; i < 3; i++) {
        digitalWrite(STATUS_LED_PIN, LOW);
        delay(200);
        digitalWrite(STATUS_LED_PIN, HIGH);
        delay(200);
    }
}

void loop() {
    // Handle WiFi connection
    if (WiFi.status() != WL_CONNECTED) {
        if (wifiConnected) {
            DEBUG_PRINTLN("WiFi connection lost, attempting reconnection...");
            wifiConnected = false;
            digitalWrite(STATUS_LED_PIN, LOW);
        }
        handleWiFiReconnection();
    } else {
        if (!wifiConnected) {
            DEBUG_PRINTLN("WiFi reconnected successfully");
            wifiConnected = true;
            digitalWrite(STATUS_LED_PIN, HIGH);
            wifiReconnectAttempts = 0;
        }
    }
    
    // Handle web server requests
    server.handleClient();
    
    // Handle OTA updates
    ArduinoOTA.handle();
    
    // Update NTP time
    timeClient.update();
    
    // Update device controller
    unsigned long loopStart = millis();
    if (deviceController) {
        deviceController->update();
    }
    
    // Update health monitor
    if (healthMonitor) {
        healthMonitor->update();
        
        // Log performance metrics
        unsigned long loopTime = millis() - loopStart;
        healthMonitor->logPerformance(loopTime, 0, 0); // Command time and queue size would be from device controller
    }
    
    // Send periodic heartbeat
    unsigned long currentTime = millis();
    if (currentTime - lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
        sendHeartbeat();
        lastHeartbeat = currentTime;
    }
    
    // Update status periodically
    if (currentTime - lastStatusUpdate >= STATUS_UPDATE_INTERVAL_MS) {
        updateStatus();
        lastStatusUpdate = currentTime;
    }
    
    delay(LOOP_DELAY_MS);
}

void setupDeviceIdentification() {
    // Get MAC address for unique device identification
    deviceMAC = WiFi.macAddress();
    deviceMAC.replace(":", "");
    
    // Generate unique device ID
    deviceId = generateDeviceId();
    
    DEBUG_PRINTF("Device MAC: %s\n", deviceMAC.c_str());
    DEBUG_PRINTF("Generated Device ID: %s\n", deviceId.c_str());
}

String generateDeviceId() {
    // Create device ID from prefix and last 6 characters of MAC
    String id = DEVICE_ID_PREFIX;
    id += deviceMAC.substring(deviceMAC.length() - 6);
    return id;
}

void setupWiFi() {
    WiFi.mode(WIFI_STA);
    WiFi.hostname(deviceId);
    
    // Try to load WiFi credentials from EEPROM or use defaults
    // For now, using hardcoded values - will be configurable via web interface
    wifiSSID = "YourWiFiNetwork";  // This should be configured
    wifiPassword = "YourWiFiPassword";  // This should be configured
    
    DEBUG_PRINTLN("WiFi setup complete, attempting connection...");
    connectToWiFi();
}

void connectToWiFi() {
    if (wifiSSID.length() == 0) {
        DEBUG_PRINTLN("No WiFi credentials configured");
        return;
    }
    
    DEBUG_PRINTF("Connecting to WiFi: %s\n", wifiSSID.c_str());
    WiFi.begin(wifiSSID.c_str(), wifiPassword.c_str());
    
    unsigned long startTime = millis();
    while (WiFi.status() != WL_CONNECTED && 
           (millis() - startTime) < WIFI_CONNECT_TIMEOUT_MS) {
        delay(500);
        DEBUG_PRINT(".");
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        DEBUG_PRINTLN("");
        DEBUG_PRINTLN("WiFi connected successfully!");
        DEBUG_PRINTF("IP Address: %s\n", WiFi.localIP().toString().c_str());
        DEBUG_PRINTF("Signal Strength: %d dBm\n", WiFi.RSSI());
    } else {
        DEBUG_PRINTLN("");
        DEBUG_PRINTLN("WiFi connection failed");
        wifiConnected = false;
    }
}

void handleWiFiReconnection() {
    if (wifiReconnectAttempts >= MAX_WIFI_RECONNECT_ATTEMPTS) {
        DEBUG_PRINTLN("Max WiFi reconnection attempts reached, restarting device...");
        ESP.restart();
        return;
    }
    
    static unsigned long lastReconnectAttempt = 0;
    unsigned long currentTime = millis();
    
    if (currentTime - lastReconnectAttempt >= WIFI_RECONNECT_INTERVAL_MS) {
        DEBUG_PRINTF("WiFi reconnection attempt %d/%d\n", 
                     wifiReconnectAttempts + 1, MAX_WIFI_RECONNECT_ATTEMPTS);
        
        WiFi.disconnect();
        delay(1000);
        connectToWiFi();
        
        wifiReconnectAttempts++;
        lastReconnectAttempt = currentTime;
    }
}

void setupWebServer() {
    server.on("/", handleRoot);
    server.on("/status", handleStatus);
    server.on("/config", HTTP_POST, handleConfig);
    server.on("/command", HTTP_POST, handleCommand);
    server.on("/health", handleHealth);
    server.on("/diagnostics", handleDiagnostics);
    server.on("/alerts", handleAlerts);
    
    server.begin();
    DEBUG_PRINTF("Web server started on port %d\n", SERVER_PORT);
}

void setupOTA() {
    ArduinoOTA.setHostname(deviceId.c_str());
    ArduinoOTA.setPassword("collision_device_ota");  // Should be configurable
    
    ArduinoOTA.onStart([]() {
        DEBUG_PRINTLN("OTA Update Starting...");
    });
    
    ArduinoOTA.onEnd([]() {
        DEBUG_PRINTLN("OTA Update Complete");
    });
    
    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        DEBUG_PRINTF("OTA Progress: %u%%\n", (progress / (total / 100)));
    });
    
    ArduinoOTA.onError([](ota_error_t error) {
        DEBUG_PRINTF("OTA Error[%u]: ", error);
        if (error == OTA_AUTH_ERROR) DEBUG_PRINTLN("Auth Failed");
        else if (error == OTA_BEGIN_ERROR) DEBUG_PRINTLN("Begin Failed");
        else if (error == OTA_CONNECT_ERROR) DEBUG_PRINTLN("Connect Failed");
        else if (error == OTA_RECEIVE_ERROR) DEBUG_PRINTLN("Receive Failed");
        else if (error == OTA_END_ERROR) DEBUG_PRINTLN("End Failed");
    });
    
    ArduinoOTA.begin();
    DEBUG_PRINTLN("OTA update service initialized");
}

void sendHeartbeat() {
    if (!wifiConnected || raspberryPiIP.length() == 0) {
        return;
    }
    
    // Create heartbeat JSON
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    doc["type"] = RESP_HEARTBEAT;
    doc["device_id"] = deviceId;
    doc["timestamp"] = timeClient.getEpochTime();
    doc["uptime"] = millis();
    doc["wifi_rssi"] = WiFi.RSSI();
    doc["free_heap"] = ESP.getFreeHeap();
    
    String heartbeatJson;
    serializeJson(doc, heartbeatJson);
    
    DEBUG_PRINTF("Sending heartbeat: %s\n", heartbeatJson.c_str());
    // TODO: Send to Raspberry Pi via HTTP POST or MQTT
}

void updateStatus() {
    // Update internal status and prepare for status requests
    DEBUG_PRINTF("Status update - Free heap: %d, WiFi RSSI: %d\n", 
                 ESP.getFreeHeap(), WiFi.RSSI());
}

void handleRoot() {
    String html = "<html><body>";
    html += "<h1>ESP8266 Collision Detection Device</h1>";
    html += "<p>Device ID: " + deviceId + "</p>";
    html += "<p>MAC Address: " + deviceMAC + "</p>";
    html += "<p>Firmware Version: " FIRMWARE_VERSION "</p>";
    html += "<p>WiFi Status: " + (wifiConnected ? "Connected" : "Disconnected") + "</p>";
    if (wifiConnected) {
        html += "<p>IP Address: " + WiFi.localIP().toString() + "</p>";
        html += "<p>Signal Strength: " + String(WiFi.RSSI()) + " dBm</p>";
    }
    html += "<p>Uptime: " + String(millis() / 1000) + " seconds</p>";
    html += "<p>Free Heap: " + String(ESP.getFreeHeap()) + " bytes</p>";
    
    // Add hardware status
    if (deviceController) {
        DeviceStatus status = deviceController->getStatus();
        html += "<h2>Hardware Status</h2>";
        html += "<p>Servo Position: " + String(status.servoPosition) + "°</p>";
        html += "<p>Relay Status: " + (status.relayStatus ? "ON" : "OFF") + "</p>";
        html += "<p>Temperature: " + String(status.temperature) + "°C</p>";
        html += "<p>LED Status: R:" + (status.ledStatus[0] ? "ON" : "OFF") + 
                " G:" + (status.ledStatus[1] ? "ON" : "OFF") + 
                " B:" + (status.ledStatus[2] ? "ON" : "OFF") + "</p>";
    }
    
    html += "</body></html>";
    
    server.send(200, "text/html", html);
}

void handleStatus() {
    if (deviceController) {
        String statusJson = deviceController->getStatusJson();
        server.send(200, "application/json", statusJson);
    } else {
        server.send(500, "application/json", "{\"error\":\"Device controller not initialized\"}");
    }
}

void handleCommand() {
    if (!deviceController) {
        server.send(500, "application/json", "{\"error\":\"Device controller not initialized\"}");
        return;
    }
    
    if (server.hasArg("plain")) {
        String commandJson = server.arg("plain");
        DEBUG_PRINTF("Received command: %s\n", commandJson.c_str());
        
        if (deviceController->handleCommand(commandJson)) {
            server.send(200, "application/json", "{\"status\":\"Command accepted\"}");
        } else {
            server.send(400, "application/json", "{\"error\":\"Invalid command\"}");
        }
    } else {
        server.send(400, "application/json", "{\"error\":\"No command data provided\"}");
    }
}

void handleHealth() {
    if (healthMonitor) {
        String healthJson = healthMonitor->getHealthReportJson();
        server.send(200, "application/json", healthJson);
    } else {
        server.send(500, "application/json", "{\"error\":\"Health monitor not initialized\"}");
    }
}

void handleDiagnostics() {
    if (healthMonitor) {
        healthMonitor->performDiagnostics();
        String diagnosticReport = healthMonitor->getDiagnosticReport();
        server.send(200, "application/json", diagnosticReport);
    } else {
        server.send(500, "application/json", "{\"error\":\"Health monitor not initialized\"}");
    }
}

void handleAlerts() {
    if (!healthMonitor) {
        server.send(500, "application/json", "{\"error\":\"Health monitor not initialized\"}");
        return;
    }
    
    if (server.method() == HTTP_GET) {
        // Get active alerts
        DynamicJsonDocument doc(JSON_BUFFER_SIZE);
        doc["device_id"] = deviceId;
        doc["active_alert_count"] = healthMonitor->getActiveAlertCount();
        
        JsonArray alertsArray = doc.createNestedArray("alerts");
        HealthAlert* alerts = healthMonitor->getAlerts();
        
        for (int i = 0; i < 10; i++) {
            if (!alerts[i].acknowledged && alerts[i].alertId.length() > 0) {
                JsonObject alert = alertsArray.createNestedObject();
                alert["id"] = alerts[i].alertId;
                alert["severity"] = alerts[i].severity;
                alert["component"] = alerts[i].component;
                alert["message"] = alerts[i].message;
                alert["timestamp"] = alerts[i].timestamp;
            }
        }
        
        String response;
        serializeJson(doc, response);
        server.send(200, "application/json", response);
        
    } else if (server.method() == HTTP_POST) {
        // Acknowledge alert
        if (server.hasArg("plain")) {
            String body = server.arg("plain");
            DynamicJsonDocument doc(JSON_BUFFER_SIZE);
            
            DeserializationError error = deserializeJson(doc, body);
            if (error) {
                server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
                return;
            }
            
            if (doc.containsKey("alert_id")) {
                String alertId = doc["alert_id"];
                healthMonitor->acknowledgeAlert(alertId);
                server.send(200, "application/json", "{\"status\":\"Alert acknowledged\"}");
            } else {
                server.send(400, "application/json", "{\"error\":\"Missing alert_id\"}");
            }
        } else {
            server.send(400, "application/json", "{\"error\":\"No data provided\"}");
        }
    } else {
        server.send(405, "application/json", "{\"error\":\"Method not allowed\"}");
    }
}

void handleConfig() {
    if (server.hasArg("plain")) {
        String body = server.arg("plain");
        DynamicJsonDocument doc(JSON_BUFFER_SIZE);
        
        DeserializationError error = deserializeJson(doc, body);
        if (error) {
            server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
            return;
        }
        
        // Update WiFi configuration
        if (doc.containsKey("wifi_ssid")) {
            wifiSSID = doc["wifi_ssid"].as<String>();
        }
        if (doc.containsKey("wifi_password")) {
            wifiPassword = doc["wifi_password"].as<String>();
        }
        if (doc.containsKey("raspberry_pi_ip")) {
            raspberryPiIP = doc["raspberry_pi_ip"].as<String>();
            // Update health monitor with Raspberry Pi IP
            if (healthMonitor) {
                healthMonitor->setRaspberryPiIP(raspberryPiIP);
            }
        }
        
        // TODO: Save configuration to EEPROM
        
        server.send(200, "application/json", "{\"status\":\"Configuration updated\"}");
        
        // Restart WiFi connection with new credentials
        if (doc.containsKey("wifi_ssid") || doc.containsKey("wifi_password")) {
            DEBUG_PRINTLN("WiFi configuration updated, reconnecting...");
            WiFi.disconnect();
            delay(1000);
            connectToWiFi();
        }
    } else {
        server.send(400, "application/json", "{\"error\":\"No configuration data provided\"}");
    }
}