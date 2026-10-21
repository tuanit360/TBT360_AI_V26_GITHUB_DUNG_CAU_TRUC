@echo off
cd /d "%~dp0"
if exist "logs\bootstrap.log" type "logs\bootstrap.log"
if exist "logs\python-installer.log" (echo. & echo ----- PYTHON INSTALL LOG ----- & powershell -NoProfile -Command "Get-Content -LiteralPath '%~dp0logs\python-installer.log' -Tail 30")
pause
