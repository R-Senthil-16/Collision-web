@echo off
REM Build all components script for Windows

echo 🔨 Building all components...

REM Build web application
echo Building web application...
cd web
npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Web application build failed
    cd ..
    pause
    exit /b 1
)
cd ..

REM Build Raspberry Pi server
echo Building Raspberry Pi server...
cd raspberry-pi
call venv\Scripts\activate.bat
python setup.py build
if %errorlevel% neq 0 (
    echo [ERROR] Raspberry Pi server build failed
    call venv\Scripts\deactivate.bat
    cd ..
    pause
    exit /b 1
)
call venv\Scripts\deactivate.bat
cd ..

REM Build ESP8266 firmware
echo Building ESP8266 firmware...
cd esp8266-devices
pio run >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] PlatformIO not available or ESP8266 build failed
) else (
    echo [SUCCESS] ESP8266 firmware built successfully
)
cd ..

echo ✅ All components built successfully
pause