#ifndef DEVICE_CONTROLLER_H
#define DEVICE_CONTROLLER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <Servo.h>

// Action types for hardware control
enum ActionType {
    ACTION_LED_ON,
    ACTION_LED_OFF,
    ACTION_LED_BLINK,
    ACTION_LED_FADE,
    ACTION_SERVO_MOVE,
    ACTION_SERVO_SWEEP,
    ACTION_RELAY_ON,
    ACTION_RELAY_OFF,
    ACTION_BUZZER_BEEP,
    ACTION_BUZZER_PATTERN,
    ACTION_STATUS_UPDATE
};

// LED color structure
struct LEDColor {
    uint8_t red;
    uint8_t green;
    uint8_t blue;
};

// Command structure
struct HardwareCommand {
    String commandId;
    ActionType action;
    int intensity;
    int duration;
    LEDColor color;
    int servoAngle;
    String pattern;
    unsigned long timestamp;
};

// Device status structure
struct DeviceStatus {
    String deviceId;
    bool wifiConnected;
    int wifiRSSI;
    unsigned long uptime;
    uint32_t freeHeap;
    bool ledStatus[3];  // RGB LED status
    int servoPosition;
    bool relayStatus;
    float temperature;
    unsigned long lastUpdate;
};

class DeviceController {
private:
    String deviceId;
    Servo servo;
    DeviceStatus currentStatus;
    HardwareCommand commandQueue[COMMAND_QUEUE_SIZE];
    int queueHead;
    int queueTail;
    int queueSize;
    
    // Hardware state
    bool ledState[3];  // RGB LED states
    int currentServoAngle;
    bool relayState;
    unsigned long lastSensorRead;
    
    // Timing variables
    unsigned long ledBlinkStart[3];
    unsigned long ledBlinkInterval[3];
    bool ledBlinking[3];
    
    // Private methods
    void initializeHardware();
    void updateLEDs();
    void updateServo();
    void updateRelay();
    void updateBuzzer();
    void readSensors();
    bool isCommandQueueFull();
    bool isCommandQueueEmpty();
    
public:
    DeviceController(String deviceId);
    
    // Initialization
    void begin();
    void connectWiFi(String ssid, String password);
    void setupHardware();
    
    // Command handling
    bool handleCommand(String commandJson);
    bool executeCommand(const HardwareCommand& command);
    void processCommandQueue();
    
    // Hardware control methods
    void setLED(int ledIndex, bool state);
    void setLEDColor(LEDColor color);
    void blinkLED(int ledIndex, int interval);
    void fadeLED(int ledIndex, int duration);
    void moveServo(int angle);
    void sweepServo(int startAngle, int endAngle, int duration);
    void setRelay(bool state);
    void beepBuzzer(int frequency, int duration);
    void playBuzzerPattern(String pattern);
    
    // Status and monitoring
    void updateStatus();
    String getStatusJson();
    DeviceStatus getStatus();
    void sendStatus();
    
    // Utility methods
    void executeAction(ActionType action, int intensity);
    void resetHardware();
    void performSelfTest();
    
    // Main update loop
    void update();
};

#endif // DEVICE_CONTROLLER_H