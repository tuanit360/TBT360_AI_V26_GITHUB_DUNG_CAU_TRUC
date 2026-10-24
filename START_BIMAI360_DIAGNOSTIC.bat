@echo off
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
echo BIMAI360 - Diagnostic launcher (console trace retained)
echo Folder: %CD%
echo Date: %DATE% %TIME%
echo URL: http://127.0.0.1:7861
set "NO_PROXY=127.0.0.1,localhost,::1,%NO_PROXY%"
set "no_proxy=127.0.0.1,localhost,::1,%no_proxy%"
if exist "BIMAI360.exe" (
  "BIMAI360.exe" > "logs\startup_console.log" 2>&1
) else (
  if exist "python\python.exe" (
    "python\python.exe" run_portable.py > "logs\startup_console.log" 2>&1
  ) else (
    py -3 run_portable.py > "logs\startup_console.log" 2>&1
  )
)
set "RESULT=%ERRORLEVEL%"
echo Exit code: %RESULT%
echo Log: %CD%\logs\startup_console.log
type "logs\startup_console.log"
echo.
echo De lay ZIP chan doan offline: EXPORT_DIAGNOSTICS_OFFLINE_WINDOWS.bat
pause
exit /b %RESULT%
