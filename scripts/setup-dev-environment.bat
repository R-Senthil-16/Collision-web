@echo off
REM Collision Detection System - Development Environment Setup Script (Windows)
REM This script sets up the complete development environment for all components

echo 🚀 Setting up Collision Detection System Development Environment
echo ==============================================================

REM Check for Node.js
echo [INFO] Checking for Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed. Please install Node.js 16+ from https://nodejs.org/
    pause
    exit /b 1
)
echo [SUCCESS] Node.js found: 
node --version

REM Check for Python
echo [INFO] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python 3.8+ from https://python.org/
    pause
    exit /b 1
)
echo [SUCCESS] Python found:
python --version

REM Setup Web Application
echo [INFO] Setting up Web Application...
cd web
if not exist "node_modules" (
    echo [INFO] Installing npm dependencies...
    npm install
)

REM Create directories
if not exist "src\core" mkdir src\core
if not exist "src\video" mkdir src\video
if not exist "src\hardware" mkdir src\hardware
if not exist "src\ui" mkdir src\ui
if not exist "src\__tests__" mkdir src\__tests__

echo [SUCCESS] Web application setup complete
cd ..

REM Setup Raspberry Pi Server
echo [INFO] Setting up Raspberry Pi Server...
cd raspberry-pi

REM Create virtual environment
if not exist "venv" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment and install dependencies
echo [INFO] Installing Python dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Create directories
if not exist "src\collision_server" mkdir src\collision_server
if not exist "src\collision_server\core" mkdir src\collision_server\core
if not exist "src\collision_server\video" mkdir src\collision_server\video
if not exist "src\collision_server\hardware" mkdir src\collision_server\hardware
if not exist "src\collision_server\cv" mkdir src\collision_server\cv
if not exist "src\collision_server\api" mkdir src\collision_server\api
if not exist "tests" mkdir tests
if not exist "logs" mkdir logs
if not exist "uploads" mkdir uploads
if not exist "processed" mkdir processed
if not exist "models" mkdir models

REM Create __init__.py files
echo. > src\__init__.py
echo. > src\collision_server\__init__.py
echo. > src\collision_server\core\__init__.py
echo. > src\collision_server\video\__init__.py
echo. > src\collision_server\hardware\__init__.py
echo. > src\collision_server\cv\__init__.py
echo. > src\collision_server\api\__init__.py

REM Copy environment file
if not exist ".env" (
    copy .env.example .env
    echo [WARNING] Created .env file from template. Please update with your configuration.
)

call venv\Scripts\deactivate.bat
echo [SUCCESS] Raspberry Pi server setup complete
cd ..

REM Setup ESP8266 Development
echo [INFO] Setting up ESP8266 Development Environment...
cd esp8266-devices

REM Create directories
if not exist "src" mkdir src
if not exist "test" mkdir test
if not exist "include\device_types" mkdir include\device_types
if not exist "lib\DeviceController\src" mkdir lib\DeviceController\src
if not exist "lib\DeviceController\include" mkdir lib\DeviceController\include

echo [INFO] ESP8266 development environment setup complete
echo [WARNING] Please install PlatformIO manually from https://platformio.org/install/cli
cd ..

REM Create project README
echo [INFO] Creating project configuration...
(
echo # Collision Detection System
echo.
echo A comprehensive collision detection system that combines web-based simulation, computer vision, and IoT hardware control.
echo.
echo ## Architecture
echo.
echo - **Web Application** ^(`web/`^): Browser-based simulation and control interface
echo - **Raspberry Pi Server** ^(`raspberry-pi/`^): Computer vision processing and hardware coordination
echo - **ESP8266 Devices** ^(`esp8266-devices/`^): IoT hardware controllers for physical responses
echo.
echo ## Quick Start
echo.
echo 1. **Setup Development Environment**:
echo    ```batch
echo    scripts\setup-dev-environment.bat
echo    ```
echo.
echo 2. **Start Web Application**:
echo    ```batch
echo    cd web
echo    npm start
echo    ```
echo.
echo 3. **Start Raspberry Pi Server**:
echo    ```batch
echo    cd raspberry-pi
echo    venv\Scripts\activate.bat
echo    python -m collision_server.main
echo    ```
echo.
echo 4. **Flash ESP8266 Device**:
echo    ```batch
echo    cd esp8266-devices
echo    pio run --target upload
echo    ```
echo.
echo ## Development
echo.
echo - **Web**: JavaScript with Canvas API, Jest for testing
echo - **Server**: Python with Flask, OpenCV, PyTorch
echo - **Hardware**: C++ with Arduino framework, PlatformIO
echo.
echo ## Testing
echo.
echo - **Web**: `cd web ^&^& npm test`
echo - **Server**: `cd raspberry-pi ^&^& python -m pytest`
echo - **Hardware**: `cd esp8266-devices ^&^& pio test`
echo.
echo See individual component READMEs for detailed information.
) > README.md

echo [SUCCESS] 🎉 Development environment setup complete!
echo.
echo Next steps:
echo 1. Review and update raspberry-pi\.env with your configuration
echo 2. Start development with: cd web ^&^& npm start
echo 3. Install PlatformIO for ESP8266 development
echo.
echo For more information, see README.md
pause