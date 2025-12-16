@echo off
echo ========================================
echo Provider Data Validation System Launcher
echo ========================================
echo.
echo Starting servers in separate windows...
echo.
start "Backend Server" cmd /k "%~dp0start-backend.bat"
timeout /t 3 /nobreak >nul
start "Frontend Server" cmd /k "%~dp0start-frontend.bat"
echo.
echo Servers are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3020
echo.
echo Close this window when done.
