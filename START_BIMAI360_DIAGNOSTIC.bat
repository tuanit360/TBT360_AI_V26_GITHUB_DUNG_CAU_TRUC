@echo off
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
echo BIM AI Kiến Trúc 360 V96 diagnostic launch
echo Folder: %CD%
echo Date: %DATE% %TIME%
echo ---------------------------------------------------------
echo To open UI manually, visit http://127.0.0.1:7861
echo ---------------------------------------------------------
"BIMAI360.exe" > "logs\startup_console.log" 2>&1
set "RESULT=%ERRORLEVEL%"
echo.
echo Exit code: %RESULT%
echo Log saved to: %CD%\logs\startup_console.log
if exist "logs\startup_error.log" echo Error saved to: %CD%\logs\startup_error.log
echo.
type "logs\startup_console.log"
echo.
pause
exit /b %RESULT%
