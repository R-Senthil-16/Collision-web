#include "DeviceController.h"
#include "config.h"
#include <ESP8266WiFi.h>

DeviceController::DeviceController(String deviceId) {
    this->deviceId = deviceId;
    queueHead = 0;
    queueTail = 0;
    queueSize = 0;
    
    // Initialize hardware state
    for (int i = 0; i < 3; i++) {
        ledState[i] = false;
        ledBlinking[i] = false;
        ledBlinkStart[i] = 0;
        ledBlinkInterval[i] = 500;
    }
    
    currentServoAngle = SERVO_DEFAULT_ANGLE;
    relayState = false;
    lastSensorRead = 0;
    
    // Initialize status
    currentStatus.deviceId = deviceId;
    currentStatus.wifiConnected = false;
    currentStatus.wifiRSSI = 0;
    currentStatus.uptime = 0;
    currentStatus.freeHeap = 0;
    currentStatus.servoPosition = SERVO_DEFAULT_ANGLE;
    currentStatus.relayStatus = false;
    currentStatus.temperature = 0.0;
    currentStatus.lastUpdate = 0;
    
    for (int i = 0; i < 3; i++) {
        currentStatus.ledStatus[i] = false;
    }
}

void DeviceController::begin() {
    DEBUG_PRINTLN("Initializing DeviceController...");
    initializeHardware();
    updateStatus();
    DEBUG_PRINTLN("DeviceController initialization complete");
}

void DeviceController::initializeHardware() {
    // Initialize LED pins
    pinMode(LED_RED_PIN, OUTPUT);
    pinMode(LED_GREEN_PIN, OUTPUT);
    pinMode(LED_BLUE_PIN, OUTPUT);
    
    // Initialize other hardware pins
    pinMode(RELAY_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(STATUS_LED_PIN, OUTPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    
    // Initialize servo
    servo.attach(SERVO_PIN);
    servo.write(SERVO_DEFAULT_ANGLE);
    
    // Set initial states
    digitalWrite(LED_RED_PIN, LOW);
    digitalWrite(LED_GREEN_PIN, LOW);
    digitalWrite(LED_BLUE_PIN, LOW);
    digitalWrite(RELAY_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(STATUS_LED_PIN, HIGH);
    
    DEBUG_PRINTLN("Hardware initialization complete");
}

void DeviceController::connectWiFi(String ssid, String password) {
    DEBUG_PRINTF("Connecting to WiFi: %s\n", ssid.c_str());
    WiFi.begin(ssid.c_str(), password.c_str());
    
    unsigned long startTime = millis();
    while (WiFi.status() != WL_CONNECTED && 
           (millis() - startTime) < WIFI_CONNECT_TIMEOUT_MS) {
        delay(500);
        DEBUG_PRINT(".");
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        currentStatus.wifiConnected = true;
        currentStatus.wifiRSSI = WiFi.RSSI();
        DEBUG_PRINTLN("\nWiFi connected successfully!");
        DEBUG_PRINTF("IP Address: %s\n", WiFi.localIP().toString().c_str());
    } else {
        currentStatus.wifiConnected = false;
        DEBUG_PRINTLN("\nWiFi connection failed");
    }
}

void DeviceController::setupHardware() {
    // Perform hardware self-test
    performSelfTest();
    
    // Set default states
    resetHardware();
    
    DEBUG_PRINTLN("Hardware setup complete");
}

bool DeviceController::handleCommand(String commandJson) {
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    DeserializationError error = deserializeJson(doc, commandJson);
    
    if (error) {
        DEBUG_PRINTF("JSON parsing failed: %s\n", error.c_str());
        return false;
    }
    
    // Validate required fields
    if (!doc.containsKey("command") || !doc.containsKey("device_id")) {
        DEBUG_PRINTLN("Missing required command fields");
        return false;
    }
    
    // Check if command is for this device
    String targetDeviceId = doc["device_id"];
    if (targetDeviceId != deviceId && targetDeviceId != "all") {
        DEBUG_PRINTF("Command not for this device: %s\n", targetDeviceId.c_str());
        return false;
    }
    
    // Parse command
    HardwareCommand command;
    command.commandId = doc.containsKey("command_id") ? doc["command_id"].as<String>() : "";
    command.timestamp = millis();
    
    String commandType = doc["command"];
    
    // Parse command type and parameters
    if (commandType == CMD_LED_CONTROL) {
        String action = doc["action"];
        if (action == "on") {
            command.action = ACTION_LED_ON;
        } else if (action == "off") {
            command.action = ACTION_LED_OFF;
        } else if (action == "blink") {
            command.action = ACTION_LED_BLINK;
        } else if (action == "fade") {
            command.action = ACTION_LED_FADE;
        } else {
            DEBUG_PRINTF("Unknown LED action: %s\n", action.c_str());
            return false;
        }
        
        command.intensity = doc.containsKey("intensity") ? doc["intensity"] : 255;
        command.duration = doc.containsKey("duration") ? doc["duration"] : 1000;
        
        if (doc.containsKey("color")) {
            command.color.red = doc["color"]["r"];
            command.color.green = doc["color"]["g"];
            command.color.blue = doc["color"]["b"];
        } else {
            command.color = {255, 255, 255}; // Default white
        }
        
    } else if (commandType == CMD_SERVO_CONTROL) {
        String action = doc["action"];
        if (action == "move") {
            command.action = ACTION_SERVO_MOVE;
        } else if (action == "sweep") {
            command.action = ACTION_SERVO_SWEEP;
        } else {
            DEBUG_PRINTF("Unknown servo action: %s\n", action.c_str());
            return false;
        }
        
        command.servoAngle = doc.containsKey("angle") ? doc["angle"] : SERVO_DEFAULT_ANGLE;
        command.duration = doc.containsKey("duration") ? doc["duration"] : 1000;
        
    } else if (commandType == CMD_RELAY_CONTROL) {
        String action = doc["action"];
        if (action == "on") {
            command.action = ACTION_RELAY_ON;
        } else if (action == "off") {
            command.action = ACTION_RELAY_OFF;
        } else {
            DEBUG_PRINTF("Unknown relay action: %s\n", action.c_str());
            return false;
        }
        
    } else if (commandType == CMD_BUZZER_CONTROL) {
        String action = doc["action"];
        if (action == "beep") {
            command.action = ACTION_BUZZER_BEEP;
        } else if (action == "pattern") {
            command.action = ACTION_BUZZER_PATTERN;
        } else {
            DEBUG_PRINTF("Unknown buzzer action: %s\n", action.c_str());
            return false;
        }
        
        command.intensity = doc.containsKey("frequency") ? doc["frequency"] : BUZZER_FREQUENCY;
        command.duration = doc.containsKey("duration") ? doc["duration"] : 500;
        command.pattern = doc.containsKey("pattern") ? doc["pattern"].as<String>() : "";
        
    } else if (commandType == CMD_STATUS_REQUEST) {
        command.action = ACTION_STATUS_UPDATE;
        
    } else {
        DEBUG_PRINTF("Unknown command type: %s\n", commandType.c_str());
        return false;
    }
    
    // Add command to queue
    if (isCommandQueueFull()) {
        DEBUG_PRINTLN("Command queue is full, dropping oldest command");
        queueHead = (queueHead + 1) % COMMAND_QUEUE_SIZE;
        queueSize--;
    }
    
    commandQueue[queueTail] = command;
    queueTail = (queueTail + 1) % COMMAND_QUEUE_SIZE;
    queueSize++;
    
    DEBUG_PRINTF("Command queued: %s\n", commandType.c_str());
    return true;
}

bool DeviceController::executeCommand(const HardwareCommand& command) {
    DEBUG_PRINTF("Executing command: %d\n", command.action);
    
    switch (command.action) {
        case ACTION_LED_ON:
            setLEDColor(command.color);
            break;
            
        case ACTION_LED_OFF:
            setLED(0, false);
            setLED(1, false);
            setLED(2, false);
            break;
            
        case ACTION_LED_BLINK:
            blinkLED(0, command.duration / 2); // Red LED
            break;
            
        case ACTION_LED_FADE:
            fadeLED(0, command.duration);
            break;
            
        case ACTION_SERVO_MOVE:
            moveServo(command.servoAngle);
            break;
            
        case ACTION_SERVO_SWEEP:
            sweepServo(0, 180, command.duration);
            break;
            
        case ACTION_RELAY_ON:
            setRelay(true);
            break;
            
        case ACTION_RELAY_OFF:
            setRelay(false);
            break;
            
        case ACTION_BUZZER_BEEP:
            beepBuzzer(command.intensity, command.duration);
            break;
            
        case ACTION_BUZZER_PATTERN:
            playBuzzerPattern(command.pattern);
            break;
            
        case ACTION_STATUS_UPDATE:
            sendStatus();
            break;
            
        default:
            DEBUG_PRINTF("Unknown action: %d\n", command.action);
            return false;
    }
    
    return true;
}

void DeviceController::processCommandQueue() {
    if (isCommandQueueEmpty()) {
        return;
    }
    
    HardwareCommand command = commandQueue[queueHead];
    if (executeCommand(command)) {
        queueHead = (queueHead + 1) % COMMAND_QUEUE_SIZE;
        queueSize--;
    }
}

void DeviceController::setLED(int ledIndex, bool state) {
    if (ledIndex < 0 || ledIndex > 2) {
        return;
    }
    
    int pins[] = {LED_RED_PIN, LED_GREEN_PIN, LED_BLUE_PIN};
    digitalWrite(pins[ledIndex], state ? HIGH : LOW);
    ledState[ledIndex] = state;
    currentStatus.ledStatus[ledIndex] = state;
    
    DEBUG_PRINTF("LED %d set to %s\n", ledIndex, state ? "ON" : "OFF");
}

void DeviceController::setLEDColor(LEDColor color) {
    analogWrite(LED_RED_PIN, color.red);
    analogWrite(LED_GREEN_PIN, color.green);
    analogWrite(LED_BLUE_PIN, color.blue);
    
    ledState[0] = color.red > 0;
    ledState[1] = color.green > 0;
    ledState[2] = color.blue > 0;
    
    currentStatus.ledStatus[0] = ledState[0];
    currentStatus.ledStatus[1] = ledState[1];
    currentStatus.ledStatus[2] = ledState[2];
    
    DEBUG_PRINTF("LED color set to RGB(%d, %d, %d)\n", color.red, color.green, color.blue);
}

void DeviceController::blinkLED(int ledIndex, int interval) {
    if (ledIndex < 0 || ledIndex > 2) {
        return;
    }
    
    ledBlinking[ledIndex] = true;
    ledBlinkInterval[ledIndex] = interval;
    ledBlinkStart[ledIndex] = millis();
    
    DEBUG_PRINTF("LED %d blinking with interval %d ms\n", ledIndex, interval);
}

void DeviceController::fadeLED(int ledIndex, int duration) {
    // Simple fade implementation - could be enhanced with PWM
    int pins[] = {LED_RED_PIN, LED_GREEN_PIN, LED_BLUE_PIN};
    
    for (int brightness = 0; brightness <= 255; brightness += 5) {
        analogWrite(pins[ledIndex], brightness);
        delay(duration / 51); // 51 steps from 0 to 255
    }
    
    for (int brightness = 255; brightness >= 0; brightness -= 5) {
        analogWrite(pins[ledIndex], brightness);
        delay(duration / 51);
    }
    
    DEBUG_PRINTF("LED %d fade complete\n", ledIndex);
}

void DeviceController::moveServo(int angle) {
    if (angle < SERVO_MIN_ANGLE || angle > SERVO_MAX_ANGLE) {
        DEBUG_PRINTF("Servo angle out of range: %d\n", angle);
        return;
    }
    
    servo.write(angle);
    currentServoAngle = angle;
    currentStatus.servoPosition = angle;
    
    DEBUG_PRINTF("Servo moved to angle: %d\n", angle);
}

void DeviceController::sweepServo(int startAngle, int endAngle, int duration) {
    int steps = abs(endAngle - startAngle);
    int stepDelay = duration / steps;
    int direction = (endAngle > startAngle) ? 1 : -1;
    
    for (int angle = startAngle; angle != endAngle; angle += direction) {
        moveServo(angle);
        delay(stepDelay);
    }
    
    moveServo(endAngle);
    DEBUG_PRINTF("Servo sweep complete: %d to %d\n", startAngle, endAngle);
}

void DeviceController::setRelay(bool state) {
    digitalWrite(RELAY_PIN, state ? HIGH : LOW);
    relayState = state;
    currentStatus.relayStatus = state;
    
    DEBUG_PRINTF("Relay set to %s\n", state ? "ON" : "OFF");
}

void DeviceController::beepBuzzer(int frequency, int duration) {
    tone(BUZZER_PIN, frequency, duration);
    DEBUG_PRINTF("Buzzer beep: %d Hz for %d ms\n", frequency, duration);
}

void DeviceController::playBuzzerPattern(String pattern) {
    // Simple pattern implementation: "short-long-short" etc.
    if (pattern == "short") {
        beepBuzzer(BUZZER_FREQUENCY, 200);
    } else if (pattern == "long") {
        beepBuzzer(BUZZER_FREQUENCY, 800);
    } else if (pattern == "double") {
        beepBuzzer(BUZZER_FREQUENCY, 200);
        delay(100);
        beepBuzzer(BUZZER_FREQUENCY, 200);
    } else if (pattern == "triple") {
        for (int i = 0; i < 3; i++) {
            beepBuzzer(BUZZER_FREQUENCY, 150);
            delay(100);
        }
    } else {
        DEBUG_PRINTF("Unknown buzzer pattern: %s\n", pattern.c_str());
    }
}

void DeviceController::updateLEDs() {
    unsigned long currentTime = millis();
    
    for (int i = 0; i < 3; i++) {
        if (ledBlinking[i]) {
            if (currentTime - ledBlinkStart[i] >= ledBlinkInterval[i]) {
                setLED(i, !ledState[i]);
                ledBlinkStart[i] = currentTime;
            }
        }
    }
}

void DeviceController::updateServo() {
    // Servo updates are handled directly in moveServo()
    // This could be enhanced for smooth movements
}

void DeviceController::updateRelay() {
    // Relay updates are handled directly in setRelay()
    // This could be enhanced for timed operations
}

void DeviceController::updateBuzzer() {
    // Buzzer updates are handled by the tone() function
    // This could be enhanced for complex patterns
}

void DeviceController::readSensors() {
    unsigned long currentTime = millis();
    
    if (currentTime - lastSensorRead >= SENSOR_READ_INTERVAL_MS) {
        // Read temperature sensor (if available)
        // For now, simulate temperature reading
        currentStatus.temperature = 25.0 + (random(-50, 50) / 10.0);
        
        lastSensorRead = currentTime;
    }
}

void DeviceController::updateStatus() {
    currentStatus.uptime = millis();
    currentStatus.freeHeap = ESP.getFreeHeap();
    currentStatus.wifiConnected = (WiFi.status() == WL_CONNECTED);
    currentStatus.wifiRSSI = WiFi.RSSI();
    currentStatus.lastUpdate = millis();
    
    readSensors();
}

String DeviceController::getStatusJson() {
    DynamicJsonDocument doc(JSON_BUFFER_SIZE);
    
    doc["type"] = RESP_STATUS;
    doc["device_id"] = currentStatus.deviceId;
    doc["wifi_connected"] = currentStatus.wifiConnected;
    doc["wifi_rssi"] = currentStatus.wifiRSSI;
    doc["uptime"] = currentStatus.uptime;
    doc["free_heap"] = currentStatus.freeHeap;
    doc["servo_position"] = currentStatus.servoPosition;
    doc["relay_status"] = currentStatus.relayStatus;
    doc["temperature"] = currentStatus.temperature;
    doc["timestamp"] = currentStatus.lastUpdate;
    
    JsonArray leds = doc.createNestedArray("led_status");
    for (int i = 0; i < 3; i++) {
        leds.add(currentStatus.ledStatus[i]);
    }
    
    String statusJson;
    serializeJson(doc, statusJson);
    
    return statusJson;
}

DeviceStatus DeviceController::getStatus() {
    return currentStatus;
}

void DeviceController::sendStatus() {
    String statusJson = getStatusJson();
    DEBUG_PRINTF("Status: %s\n", statusJson.c_str());
    // TODO: Send status to Raspberry Pi via HTTP or MQTT
}

void DeviceController::executeAction(ActionType action, int intensity) {
    HardwareCommand command;
    command.action = action;
    command.intensity = intensity;
    command.timestamp = millis();
    
    executeCommand(command);
}

void DeviceController::resetHardware() {
    // Reset all hardware to default states
    setLED(0, false);
    setLED(1, false);
    setLED(2, false);
    moveServo(SERVO_DEFAULT_ANGLE);
    setRelay(false);
    
    // Stop any blinking
    for (int i = 0; i < 3; i++) {
        ledBlinking[i] = false;
    }
    
    DEBUG_PRINTLN("Hardware reset to default states");
}

void DeviceController::performSelfTest() {
    DEBUG_PRINTLN("Performing hardware self-test...");
    
    // Test LEDs
    for (int i = 0; i < 3; i++) {
        setLED(i, true);
        delay(200);
        setLED(i, false);
        delay(100);
    }
    
    // Test servo
    moveServo(45);
    delay(500);
    moveServo(135);
    delay(500);
    moveServo(SERVO_DEFAULT_ANGLE);
    delay(500);
    
    // Test relay
    setRelay(true);
    delay(200);
    setRelay(false);
    
    // Test buzzer
    beepBuzzer(BUZZER_FREQUENCY, 200);
    delay(300);
    
    DEBUG_PRINTLN("Self-test complete");
}

void DeviceController::update() {
    // Process pending commands
    processCommandQueue();
    
    // Update hardware states
    updateLEDs();
    updateServo();
    updateRelay();
    updateBuzzer();
    
    // Update status periodically
    static unsigned long lastStatusUpdate = 0;
    if (millis() - lastStatusUpdate >= STATUS_UPDATE_INTERVAL_MS) {
        updateStatus();
        lastStatusUpdate = millis();
    }
}

bool DeviceController::isCommandQueueFull() {
    return queueSize >= COMMAND_QUEUE_SIZE;
}

bool DeviceController::isCommandQueueEmpty() {
    return queueSize == 0;
}