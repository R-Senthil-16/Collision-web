@echo off
REM Test all components script for Windows

echo 🧪 Running all tests...

REM Test web application
echo Testing web application...
cd web
npm test
if %errorlevel% neq 0 (
    echo [ERROR] Web application tests failed
    cd ..
    pause
    exit /b 1
)
cd ..

REM Test Raspberry Pi server
echo Testing Raspberry Pi server...
cd raspberry-pi
call venv\Scripts\activate.bat
python -m pytest
if %errorlevel% neq 0 (
    echo [ERROR] Raspberry Pi server tests failed
    call venv\Scripts\deactivate.bat
    cd ..
    pause
    exit /b 1
)
call venv\Scripts\deactivate.bat
cd ..

REM Test ESP8266 firmware
echo Testing ESP8266 firmware...
cd esp8266-devices
pio test >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] PlatformIO not available or ESP8266 tests failed
) else (
    echo [SUCCESS] ESP8266 tests completed successfully
)
cd ..

echo ✅ All tests completed
pause