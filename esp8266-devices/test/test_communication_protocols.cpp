#include <unity.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include "config.h"

// Test communication protocol parsing and validation
void test_json_command_parsing() {
    // Test valid LED command
    String validCommand = R"({"command": "led_control", "device_id": "TEST_001", "action": "on", "color": {"r": 255, "g": 0, "b": 0}, "intensity": 255, "duration": 1000})";
    
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(doc, validCommand);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_TRUE(doc.containsKey("command"));
    TEST_ASSERT_TRUE(doc.containsKey("device_id"));
    TEST_ASSERT_TRUE(doc.containsKey("action"));
    TEST_ASSERT_EQUAL_STRING("led_control", doc["command"]);
    TEST_ASSERT_EQUAL_STRING("TEST_001", doc["device_id"]);
    TEST_ASSERT_EQUAL_STRING("on", doc["action"]);
    TEST_ASSERT_EQUAL(255, doc["intensity"]);
}

// Test status response generation
void test_status_response_generation() {
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    
    doc["type"] = RESP_STATUS;
    doc["device_id"] = "TEST_001";
    doc["wifi_connected"] = true;
    doc["wifi_rssi"] = -45;
    doc["uptime"] = 12345;
    doc["free_heap"] = 25000;
    doc["servo_position"] = 90;
    doc["relay_status"] = false;
    doc["temperature"] = 25.5;
    doc["timestamp"] = millis();
    
    JsonArray leds = doc.createNestedArray("led_status");
    leds.add(true);
    leds.add(false);
    leds.add(true);
    
    String response;
    serializeJson(doc, response);
    
    // Verify the JSON is valid
    DynamicJsonDocument testDoc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(testDoc, response);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_EQUAL_STRING(RESP_STATUS, testDoc["type"]);
    TEST_ASSERT_EQUAL_STRING("TEST_001", testDoc["device_id"]);
    TEST_ASSERT_TRUE(testDoc["wifi_connected"]);
    TEST_ASSERT_EQUAL(-45, testDoc["wifi_rssi"]);
}

// Test heartbeat message format
void test_heartbeat_message_format() {
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    
    doc["type"] = RESP_HEARTBEAT;
    doc["device_id"] = "TEST_001";
    doc["timestamp"] = millis();
    doc["uptime"] = 54321;
    doc["wifi_rssi"] = -50;
    doc["free_heap"] = 20000;
    
    String heartbeat;
    serializeJson(doc, heartbeat);
    
    // Verify heartbeat format
    DynamicJsonDocument testDoc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(testDoc, heartbeat);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_EQUAL_STRING(RESP_HEARTBEAT, testDoc["type"]);
    TEST_ASSERT_TRUE(testDoc.containsKey("timestamp"));
    TEST_ASSERT_TRUE(testDoc.containsKey("uptime"));
    TEST_ASSERT_TRUE(testDoc.containsKey("wifi_rssi"));
    TEST_ASSERT_TRUE(testDoc.containsKey("free_heap"));
}

// Test error response format
void test_error_response_format() {
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    
    doc["type"] = RESP_ERROR;
    doc["device_id"] = "TEST_001";
    doc["error_code"] = ERROR_INVALID_COMMAND;
    doc["error_message"] = "Invalid command received";
    doc["timestamp"] = millis();
    
    String errorResponse;
    serializeJson(doc, errorResponse);
    
    // Verify error format
    DynamicJsonDocument testDoc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(testDoc, errorResponse);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_EQUAL_STRING(RESP_ERROR, testDoc["type"]);
    TEST_ASSERT_EQUAL(ERROR_INVALID_COMMAND, testDoc["error_code"]);
    TEST_ASSERT_EQUAL_STRING("Invalid command received", testDoc["error_message"]);
}

// Test command validation
void test_command_validation() {
    // Test missing required fields
    String missingCommand = R"({"action": "on"})";
    
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(doc, missingCommand);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_FALSE(doc.containsKey("command"));
    TEST_ASSERT_FALSE(doc.containsKey("device_id"));
    
    // Test malformed JSON
    String malformedJson = R"({"command": "led_control" "device_id": "TEST_001"})";
    
    DynamicJsonDocument doc2(JSON_BUFFER_SIZE);
    DeserializationError error2 = deserializeJson(doc2, malformedJson);
    
    TEST_ASSERT_NOT_EQUAL(DeserializationError::Ok, error2);
}

// Test servo command validation
void test_servo_command_validation() {
    // Test valid servo command
    String validServoCommand = R"({"command": "servo_control", "device_id": "TEST_001", "action": "move", "angle": 90})";
    
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(doc, validServoCommand);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_EQUAL_STRING("servo_control", doc["command"]);
    TEST_ASSERT_EQUAL_STRING("move", doc["action"]);
    TEST_ASSERT_EQUAL(90, doc["angle"]);
    
    // Validate angle range
    int angle = doc["angle"];
    TEST_ASSERT_TRUE(angle >= SERVO_MIN_ANGLE && angle <= SERVO_MAX_ANGLE);
}

// Test relay command validation
void test_relay_command_validation() {
    // Test relay ON command
    String relayOnCommand = R"({"command": "relay_control", "device_id": "TEST_001", "action": "on"})";
    
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(doc, relayOnCommand);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_EQUAL_STRING("relay_control", doc["command"]);
    TEST_ASSERT_EQUAL_STRING("on", doc["action"]);
    
    // Test relay OFF command
    String relayOffCommand = R"({"command": "relay_control", "device_id": "TEST_001", "action": "off"})";
    
    DynamicJsonDocument doc2(JSON_BUFFER_SIZE);
    DeserializationError error2 = deserializeJson(doc2, relayOffCommand);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error2);
    TEST_ASSERT_EQUAL_STRING("off", doc2["action"]);
}

// Test buzzer command validation
void test_buzzer_command_validation() {
    // Test buzzer beep command
    String buzzerCommand = R"({"command": "buzzer_control", "device_id": "TEST_001", "action": "beep", "frequency": 2000, "duration": 500})";
    
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(doc, buzzerCommand);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_EQUAL_STRING("buzzer_control", doc["command"]);
    TEST_ASSERT_EQUAL_STRING("beep", doc["action"]);
    TEST_ASSERT_EQUAL(2000, doc["frequency"]);
    TEST_ASSERT_EQUAL(500, doc["duration"]);
    
    // Validate frequency range (reasonable audio frequency)
    int frequency = doc["frequency"];
    TEST_ASSERT_TRUE(frequency >= 100 && frequency <= 10000);
}

// Test LED color validation
void test_led_color_validation() {
    String ledColorCommand = R"({"command": "led_control", "device_id": "TEST_001", "action": "on", "color": {"r": 255, "g": 128, "b": 0}, "intensity": 200})";
    
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(doc, ledColorCommand);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_TRUE(doc.containsKey("color"));
    
    JsonObject color = doc["color"];
    TEST_ASSERT_EQUAL(255, color["r"]);
    TEST_ASSERT_EQUAL(128, color["g"]);
    TEST_ASSERT_EQUAL(0, color["b"]);
    
    // Validate color values are in valid range (0-255)
    TEST_ASSERT_TRUE(color["r"] >= 0 && color["r"] <= 255);
    TEST_ASSERT_TRUE(color["g"] >= 0 && color["g"] <= 255);
    TEST_ASSERT_TRUE(color["b"] >= 0 && color["b"] <= 255);
}

// Test broadcast command handling
void test_broadcast_command_handling() {
    String broadcastCommand = R"({"command": "status_request", "device_id": "all"})";
    
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(doc, broadcastCommand);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_EQUAL_STRING("all", doc["device_id"]);
    
    // Verify broadcast handling logic
    String deviceId = doc["device_id"];
    bool shouldProcess = (deviceId == "TEST_001" || deviceId == "all");
    TEST_ASSERT_TRUE(shouldProcess);
}

// Test acknowledgment message format
void test_acknowledgment_message_format() {
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    
    doc["type"] = RESP_ACK;
    doc["device_id"] = "TEST_001";
    doc["command_id"] = "CMD_12345";
    doc["status"] = "success";
    doc["timestamp"] = millis();
    
    String ackMessage;
    serializeJson(doc, ackMessage);
    
    // Verify acknowledgment format
    DynamicJsonDocument testDoc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(testDoc, ackMessage);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_EQUAL_STRING(RESP_ACK, testDoc["type"]);
    TEST_ASSERT_EQUAL_STRING("TEST_001", testDoc["device_id"]);
    TEST_ASSERT_EQUAL_STRING("CMD_12345", testDoc["command_id"]);
    TEST_ASSERT_EQUAL_STRING("success", testDoc["status"]);
}

// Test large JSON handling
void test_large_json_handling() {
    // Create a large JSON document
    DynamicJsonDocument largeDoc(JSON_BUFFER_SIZE * 2);
    
    largeDoc["command"] = "led_control";
    largeDoc["device_id"] = "TEST_001";
    largeDoc["action"] = "pattern";
    
    // Add a large array
    JsonArray pattern = largeDoc.createNestedArray("pattern_data");
    for (int i = 0; i < 50; i++) {
        JsonObject step = pattern.createNestedObject();
        step["step"] = i;
        step["color"] = "rgb(" + String(i * 5) + ",128,255)";
        step["duration"] = 100 + i * 10;
    }
    
    String largeJson;
    serializeJson(largeDoc, largeJson);
    
    // Try to parse it back (should handle gracefully if too large)
    DynamicJsonDocument testDoc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(testDoc, largeJson);
    
    // Either it parses successfully or fails gracefully
    TEST_ASSERT_TRUE(error == DeserializationError::Ok || error == DeserializationError::NoMemory);
}

void setup() {
    delay(2000); // Wait for serial monitor
    
    UNITY_BEGIN();
    
    RUN_TEST(test_json_command_parsing);
    RUN_TEST(test_status_response_generation);
    RUN_TEST(test_heartbeat_message_format);
    RUN_TEST(test_error_response_format);
    RUN_TEST(test_command_validation);
    RUN_TEST(test_servo_command_validation);
    RUN_TEST(test_relay_command_validation);
    RUN_TEST(test_buzzer_command_validation);
    RUN_TEST(test_led_color_validation);
    RUN_TEST(test_broadcast_command_handling);
    RUN_TEST(test_acknowledgment_message_format);
    RUN_TEST(test_large_json_handling);
    
    UNITY_END();
}

void loop() {
    // Empty loop for testing
}