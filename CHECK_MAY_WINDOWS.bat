@echo off
cd /d "%~dp0"
set "PYTHON="
for /f "usebackq delims=" %%P in ("runtime\active_python.txt") do set "PYTHON=%%P"
if not exist "runtime\active_python.txt" (echo [LOI] Hay chay CHAY_TBT360_AI_WINDOWS.bat de cai moi truong truoc. & pause & exit /b 1)
"%PYTHON%" tools\preflight.py
pause
