@echo off
echo.
echo ========================================
echo    PersonaBot — Starting Server
echo ========================================
echo.

cd backend
call venv\Scripts\activate.bat 2>nul || (
    echo [INFO] No venv found. Using system Python.
)

echo [*] Starting backend on http://localhost:5000
echo [*] Open http://localhost:5000 in your browser
echo.
python app.py
pause
