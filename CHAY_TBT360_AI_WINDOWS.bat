@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
echo ======================================
echo TBT360 AI V65 - CAI 1 LAN, CHAY NHIEU LAN
echo ======================================
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0SETUP_AND_RUN.ps1"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo [ERROR] Khong the khoi dong. Xem logs\bootstrap.log
  pause
)
exit /b %RC%
