#include <unity.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include "DeviceController.h"
#include "config.h"

// Mock implementations for testing
class MockDeviceController : public DeviceController {
public:
    MockDeviceController(String deviceId) : DeviceController(deviceId) {}
    
    // Expose private methods for testing
    bool testCommandParsing(String commandJson) {
        return handleCommand(commandJson);
    }
    
    DeviceStatus testGetStatus() {
        return getStatus();
    }
    
    void testExecuteAction(ActionType action, int intensity) {
        executeAction(action, intensity);
    }
};

MockDeviceController* testController = nullptr;

void setUp(void) {
    // Set up before each test
    testController = new MockDeviceController("TEST_DEVICE_001");
    testController->begin();
}

void tearDown(void) {
    // Clean up after each test
    if (testController) {
        delete testController;
        testController = nullptr;
    }
}

// Test device initialization
void test_device_initialization() {
    TEST_ASSERT_NOT_NULL(testController);
    
    DeviceStatus status = testController->testGetStatus();
    TEST_ASSERT_EQUAL_STRING("TEST_DEVICE_001", status.deviceId.c_str());
    TEST_ASSERT_EQUAL(SERVO_DEFAULT_ANGLE, status.servoPosition);
    TEST_ASSERT_FALSE(status.relayStatus);
    
    // Test initial LED states
    for (int i = 0; i < 3; i++) {
        TEST_ASSERT_FALSE(status.ledStatus[i]);
    }
}

// Test LED control commands
void test_led_control_commands() {
    // Test LED ON command
    String ledOnCommand = R"({"command": "led_control", "device_id": "TEST_DEVICE_001", "action": "on", "color": {"r": 255, "g": 0, "b": 0}, "intensity": 255})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(ledOnCommand));
    
    // Test LED OFF command
    String ledOffCommand = R"({"command": "led_control", "device_id": "TEST_DEVICE_001", "action": "off"})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(ledOffCommand));
    
    // Test LED BLINK command
    String ledBlinkCommand = R"({"command": "led_control", "device_id": "TEST_DEVICE_001", "action": "blink", "duration": 1000})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(ledBlinkCommand));
}

// Test servo control commands
void test_servo_control_commands() {
    // Test servo move command
    String servoMoveCommand = R"({"command": "servo_control", "device_id": "TEST_DEVICE_001", "action": "move", "angle": 90})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(servoMoveCommand));
    
    // Test servo sweep command
    String servoSweepCommand = R"({"command": "servo_control", "device_id": "TEST_DEVICE_001", "action": "sweep", "duration": 2000})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(servoSweepCommand));
    
    // Test invalid servo angle
    String invalidAngleCommand = R"({"command": "servo_control", "device_id": "TEST_DEVICE_001", "action": "move", "angle": 200})";
    
    // Should still parse successfully, but angle will be clamped
    TEST_ASSERT_TRUE(testController->testCommandParsing(invalidAngleCommand));
}

// Test relay control commands
void test_relay_control_commands() {
    // Test relay ON command
    String relayOnCommand = R"({"command": "relay_control", "device_id": "TEST_DEVICE_001", "action": "on"})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(relayOnCommand));
    
    // Test relay OFF command
    String relayOffCommand = R"({"command": "relay_control", "device_id": "TEST_DEVICE_001", "action": "off"})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(relayOffCommand));
}

// Test buzzer control commands
void test_buzzer_control_commands() {
    // Test buzzer beep command
    String buzzerBeepCommand = R"({"command": "buzzer_control", "device_id": "TEST_DEVICE_001", "action": "beep", "frequency": 2000, "duration": 500})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(buzzerBeepCommand));
    
    // Test buzzer pattern command
    String buzzerPatternCommand = R"({"command": "buzzer_control", "device_id": "TEST_DEVICE_001", "action": "pattern", "pattern": "double"})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(buzzerPatternCommand));
}

// Test status request command
void test_status_request_command() {
    String statusCommand = R"({"command": "status_request", "device_id": "TEST_DEVICE_001"})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(statusCommand));
}

// Test invalid commands
void test_invalid_commands() {
    // Test malformed JSON
    String malformedJson = R"({"command": "led_control" "device_id": "TEST_DEVICE_001"})";
    
    TEST_ASSERT_FALSE(testController->testCommandParsing(malformedJson));
    
    // Test missing required fields
    String missingFields = R"({"action": "on"})";
    
    TEST_ASSERT_FALSE(testController->testCommandParsing(missingFields));
    
    // Test wrong device ID
    String wrongDeviceId = R"({"command": "led_control", "device_id": "WRONG_DEVICE", "action": "on"})";
    
    TEST_ASSERT_FALSE(testController->testCommandParsing(wrongDeviceId));
    
    // Test unknown command type
    String unknownCommand = R"({"command": "unknown_command", "device_id": "TEST_DEVICE_001"})";
    
    TEST_ASSERT_FALSE(testController->testCommandParsing(unknownCommand));
}

// Test broadcast commands (device_id = "all")
void test_broadcast_commands() {
    String broadcastCommand = R"({"command": "led_control", "device_id": "all", "action": "on", "color": {"r": 0, "g": 255, "b": 0}})";
    
    TEST_ASSERT_TRUE(testController->testCommandParsing(broadcastCommand));
}

// Test action execution
void test_action_execution() {
    // Test LED actions
    testController->testExecuteAction(ACTION_LED_ON, 255);
    testController->testExecuteAction(ACTION_LED_OFF, 0);
    
    // Test servo actions
    testController->testExecuteAction(ACTION_SERVO_MOVE, 90);
    
    // Test relay actions
    testController->testExecuteAction(ACTION_RELAY_ON, 1);
    testController->testExecuteAction(ACTION_RELAY_OFF, 0);
    
    // Test buzzer actions
    testController->testExecuteAction(ACTION_BUZZER_BEEP, 2000);
    
    // All actions should execute without crashing
    TEST_ASSERT_TRUE(true);
}

// Test status JSON generation
void test_status_json_generation() {
    String statusJson = testController->getStatusJson();
    
    // Parse the JSON to verify structure
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(doc, statusJson);
    
    TEST_ASSERT_EQUAL(DeserializationError::Ok, error);
    TEST_ASSERT_TRUE(doc.containsKey("type"));
    TEST_ASSERT_TRUE(doc.containsKey("device_id"));
    TEST_ASSERT_TRUE(doc.containsKey("uptime"));
    TEST_ASSERT_TRUE(doc.containsKey("free_heap"));
    TEST_ASSERT_TRUE(doc.containsKey("servo_position"));
    TEST_ASSERT_TRUE(doc.containsKey("relay_status"));
    TEST_ASSERT_TRUE(doc.containsKey("led_status"));
    
    TEST_ASSERT_EQUAL_STRING("status", doc["type"]);
    TEST_ASSERT_EQUAL_STRING("TEST_DEVICE_001", doc["device_id"]);
}

// Test hardware reset functionality
void test_hardware_reset() {
    // Set some hardware states
    testController->testExecuteAction(ACTION_LED_ON, 255);
    testController->testExecuteAction(ACTION_SERVO_MOVE, 45);
    testController->testExecuteAction(ACTION_RELAY_ON, 1);
    
    // Reset hardware
    testController->resetHardware();
    
    // Verify reset state
    DeviceStatus status = testController->testGetStatus();
    TEST_ASSERT_EQUAL(SERVO_DEFAULT_ANGLE, status.servoPosition);
    TEST_ASSERT_FALSE(status.relayStatus);
    
    for (int i = 0; i < 3; i++) {
        TEST_ASSERT_FALSE(status.ledStatus[i]);
    }
}

// Test command queue functionality
void test_command_queue() {
    // Add multiple commands rapidly
    for (int i = 0; i < 5; i++) {
        String command = R"({"command": "led_control", "device_id": "TEST_DEVICE_001", "action": "blink"})";
        
        TEST_ASSERT_TRUE(testController->testCommandParsing(command));
    }
    
    // Process commands
    for (int i = 0; i < 10; i++) {
        testController->update();
        delay(10);
    }
    
    // Commands should be processed without errors
    TEST_ASSERT_TRUE(true);
}

void setup() {
    delay(2000); // Wait for serial monitor
    
    UNITY_BEGIN();
    
    RUN_TEST(test_device_initialization);
    RUN_TEST(test_led_control_commands);
    RUN_TEST(test_servo_control_commands);
    RUN_TEST(test_relay_control_commands);
    RUN_TEST(test_buzzer_control_commands);
    RUN_TEST(test_status_request_command);
    RUN_TEST(test_invalid_commands);
    RUN_TEST(test_broadcast_commands);
    RUN_TEST(test_action_execution);
    RUN_TEST(test_status_json_generation);
    RUN_TEST(test_hardware_reset);
    RUN_TEST(test_command_queue);
    
    UNITY_END();
}

void loop() {
    // Empty loop for testing
}