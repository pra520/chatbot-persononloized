@echo off
echo.
echo ========================================
echo    PersonaBot — Setup Script
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed. Please install Python 3.9+ from python.org
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
cd backend
python -m venv venv
call venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
pip install -r requirements.txt

echo [3/4] Creating .env file...
if not exist .env (
    copy .env.example .env
    echo [INFO] Created .env — please add your OpenRouter API key!
    echo        Open: backend\.env
) else (
    echo [INFO] .env already exists
)

echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo NEXT STEPS:
echo   1. Open backend\.env
echo   2. Replace 'your_openrouter_api_key_here' with your real key
echo   3. Run: start.bat
echo.
pause
