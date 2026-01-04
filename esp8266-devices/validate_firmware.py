#!/usr/bin/env python3
"""
ESP8266 Firmware Validation Script
Validates the firmware code structure and configuration
"""

import os
import re
import json

def check_file_exists(filepath):
    """Check if a file exists"""
    return os.path.exists(filepath)

def check_config_definitions():
    """Check that all required configuration definitions exist"""
    config_file = "include/config.h"
    if not check_file_exists(config_file):
        return False, "config.h not found"
    
    with open(config_file, 'r') as f:
        content = f.read()
    
    required_defines = [
        'DEVICE_TYPE',
        'FIRMWARE_VERSION',
        'DEVICE_ID_PREFIX',
        'LED_RED_PIN',
        'LED_GREEN_PIN',
        'LED_BLUE_PIN',
        'SERVO_PIN',
        'RELAY_PIN',
        'BUZZER_PIN',
        'CMD_LED_CONTROL',
        'CMD_SERVO_CONTROL',
        'CMD_RELAY_CONTROL',
        'RESP_STATUS',
        'RESP_ACK',
        'RESP_ERROR'
    ]
    
    missing_defines = []
    for define in required_defines:
        if f'#define {define}' not in content:
            missing_defines.append(define)
    
    if missing_defines:
        return False, f"Missing defines: {', '.join(missing_defines)}"
    
    return True, "All configuration definitions found"

def check_class_definitions():
    """Check that required classes are defined"""
    files_to_check = [
        ("include/DeviceController.h", "class DeviceController"),
        ("include/HealthMonitor.h", "class HealthMonitor"),
        ("src/DeviceController.cpp", "DeviceController::DeviceController"),
        ("src/HealthMonitor.cpp", "HealthMonitor::HealthMonitor")
    ]
    
    for filepath, pattern in files_to_check:
        if not check_file_exists(filepath):
            return False, f"File not found: {filepath}"
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        if pattern not in content:
            return False, f"Pattern '{pattern}' not found in {filepath}"
    
    return True, "All required classes found"

def check_main_structure():
    """Check main.cpp structure"""
    main_file = "src/main.cpp"
    if not check_file_exists(main_file):
        return False, "main.cpp not found"
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    required_functions = [
        'void setup()',
        'void loop()',
        'void setupWiFi()',
        'void setupDeviceIdentification()',
        'void setupWebServer()',
        'void handleCommand()',
        'void handleStatus()',
        'void handleHealth()'
    ]
    
    missing_functions = []
    for func in required_functions:
        if func not in content:
            missing_functions.append(func)
    
    if missing_functions:
        return False, f"Missing functions: {', '.join(missing_functions)}"
    
    return True, "Main structure is correct"

def check_test_files():
    """Check that test files exist and have basic structure"""
    test_files = [
        "test/test_device_controller.cpp",
        "test/test_health_monitor.cpp",
        "test/test_communication_protocols.cpp",
        "test/test_runner.cpp"
    ]
    
    for test_file in test_files:
        if not check_file_exists(test_file):
            return False, f"Test file not found: {test_file}"
        
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Check for basic test structure
        if 'void setup()' not in content and 'RUN_TEST(' not in content and 'test_' not in content:
            return False, f"Test file {test_file} doesn't have proper test structure"
    
    return True, "All test files found and structured correctly"

def check_platformio_config():
    """Check PlatformIO configuration"""
    config_file = "platformio.ini"
    if not check_file_exists(config_file):
        return False, "platformio.ini not found"
    
    with open(config_file, 'r') as f:
        content = f.read()
    
    required_sections = [
        '[env:esp8266_generic]',
        '[env:native]',
        'test_framework = unity'
    ]
    
    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)
    
    if missing_sections:
        return False, f"Missing PlatformIO sections: {', '.join(missing_sections)}"
    
    return True, "PlatformIO configuration is correct"

def validate_json_examples():
    """Validate JSON command examples in test files"""
    test_files = [
        "test/test_device_controller.cpp",
        "test/test_communication_protocols.cpp"
    ]
    
    json_pattern = r'R"\(({.*?})\)"'
    
    for test_file in test_files:
        if not check_file_exists(test_file):
            continue
        
        with open(test_file, 'r') as f:
            content = f.read()
        
        json_matches = re.findall(json_pattern, content, re.DOTALL)
        
        for json_str in json_matches:
            # Skip intentionally malformed JSON (used for testing error handling)
            if 'malformedJson' in content and '"command": "led_control" "device_id"' in json_str:
                continue  # This is intentionally malformed for testing
            
            try:
                json.loads(json_str)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON in {test_file}: {e} - JSON: {json_str[:100]}..."
    
    return True, "All JSON examples are valid"

def main():
    """Main validation function"""
    print("ESP8266 Firmware Validation")
    print("=" * 40)
    
    checks = [
        ("Configuration definitions", check_config_definitions),
        ("Class definitions", check_class_definitions),
        ("Main structure", check_main_structure),
        ("Test files", check_test_files),
        ("PlatformIO configuration", check_platformio_config),
        ("JSON examples", validate_json_examples)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"Checking {check_name}... ", end="")
        try:
            passed, message = check_func()
            if passed:
                print("PASS")
            else:
                print(f"FAIL - {message}")
                all_passed = False
        except Exception as e:
            print(f"ERROR - {e}")
            all_passed = False
    
    print("=" * 40)
    if all_passed:
        print("All validation checks PASSED!")
        return 0
    else:
        print("Some validation checks FAILED!")
        return 1

if __name__ == "__main__":
    exit(main())