@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
echo BIMAI360 V271 - nhat ky offline
echo Nhat ky mo trong Notepad, co the Ctrl+A va Ctrl+C.
if exist "logs\runtime_errors.log" (
  start "" notepad "logs\runtime_errors.log"
) else (
  echo Chua co runtime_errors.log > "logs\LOG_CHAN_DOAN.txt"
  start "" notepad "logs\LOG_CHAN_DOAN.txt"
)
if exist "logs\bimai360_operations.log" start "" notepad "logs\bimai360_operations.log"
if exist "logs\startup_error.log" start "" notepad "logs\startup_error.log"
if exist "BIMAI360.exe" "BIMAI360.exe" --diagnostics
echo Kiem tra thu muc logs de tim ZIP chan doan.
pause
