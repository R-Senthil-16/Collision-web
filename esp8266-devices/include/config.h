#ifndef CONFIG_H
#define CONFIG_H

// Device Configuration
#define DEVICE_TYPE "ESP8266_COLLISION_CONTROLLER"
#define FIRMWARE_VERSION "1.0.0"
#define DEVICE_ID_PREFIX "COL_"

// WiFi Configuration
#define WIFI_CONNECT_TIMEOUT_MS 30000
#define WIFI_RECONNECT_INTERVAL_MS 5000
#define MAX_WIFI_RECONNECT_ATTEMPTS 10

// Network Configuration
#define SERVER_PORT 8266
#define DISCOVERY_PORT 8267
#define HEARTBEAT_INTERVAL_MS 30000
#define COMMAND_TIMEOUT_MS 5000

// Hardware Pin Definitions
#define LED_RED_PIN D1
#define LED_GREEN_PIN D2
#define LED_BLUE_PIN D3
#define SERVO_PIN D4
#define RELAY_PIN D5
#define BUZZER_PIN D6
#define STATUS_LED_PIN D7
#define BUTTON_PIN D8

// Hardware Configuration
#define SERVO_MIN_ANGLE 0
#define SERVO_MAX_ANGLE 180
#define SERVO_DEFAULT_ANGLE 90
#define LED_PWM_FREQUENCY 1000
#define BUZZER_FREQUENCY 2000

// Communication Configuration
#define MQTT_KEEPALIVE 60
#define MQTT_QOS 1
#define JSON_BUFFER_SIZE 512
#define COMMAND_QUEUE_SIZE 10

// Timing Configuration
#define LOOP_DELAY_MS 10
#define STATUS_UPDATE_INTERVAL_MS 1000
#define SENSOR_READ_INTERVAL_MS 500
#define WATCHDOG_TIMEOUT_MS 8000

// Debug Configuration
#ifdef DEBUG
    #define DEBUG_PRINT(x) Serial.print(x)
    #define DEBUG_PRINTLN(x) Serial.println(x)
    #define DEBUG_PRINTF(format, ...) Serial.printf(format, ##__VA_ARGS__)
#else
    #define DEBUG_PRINT(x)
    #define DEBUG_PRINTLN(x)
    #define DEBUG_PRINTF(format, ...)
#endif

// Error Codes
#define ERROR_NONE 0
#define ERROR_WIFI_CONNECTION 1
#define ERROR_SERVER_CONNECTION 2
#define ERROR_INVALID_COMMAND 3
#define ERROR_HARDWARE_FAILURE 4
#define ERROR_MEMORY_ALLOCATION 5
#define ERROR_JSON_PARSE 6
#define ERROR_TIMEOUT 7

// Command Types
#define CMD_LED_CONTROL "led_control"
#define CMD_SERVO_CONTROL "servo_control"
#define CMD_RELAY_CONTROL "relay_control"
#define CMD_BUZZER_CONTROL "buzzer_control"
#define CMD_STATUS_REQUEST "status_request"
#define CMD_RESET_DEVICE "reset_device"
#define CMD_UPDATE_CONFIG "update_config"

// Response Types
#define RESP_STATUS "status"
#define RESP_ACK "acknowledgment"
#define RESP_ERROR "error"
#define RESP_HEARTBEAT "heartbeat"

#endif // CONFIG_H