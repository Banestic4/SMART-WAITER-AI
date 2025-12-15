@echo off
echo Starting Smart Waiter Local Test Environment...

:: Start Backend
start "Smart Waiter Backend" cmd /k "echo Starting Backend... & python -m uvicorn api.index:app --reload --port 8000"

:: Wait a moment for backend
timeout /t 5

:: Start Frontend
cd smart-waiter-ui
start "Smart Waiter Frontend" cmd /k "echo Starting Frontend... & npm run dev"

echo.
echo Environment starting! 
echo Backend running on http://localhost:8000
echo Frontend running on http://localhost:3000
echo.
pause
