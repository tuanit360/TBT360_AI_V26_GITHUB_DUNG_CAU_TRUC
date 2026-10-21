@echo off
cd /d "%~dp0"
set "PYTHON="
for /f "usebackq delims=" %%P in ("runtime\active_python.txt") do set "PYTHON=%%P"
if not exist "runtime\active_python.txt" (echo Chay CHAY_TBT360_AI_WINDOWS.bat truoc. & pause & exit /b 1)
"%PYTHON%" tools\validate_dataset.py
pause
