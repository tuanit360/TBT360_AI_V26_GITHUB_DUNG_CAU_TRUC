@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Chay BUILD_WINDOWS_X64.bat truoc de tao venv & pause & exit /b 1)
.venv\Scripts\python.exe tools\download_model.py
pause
