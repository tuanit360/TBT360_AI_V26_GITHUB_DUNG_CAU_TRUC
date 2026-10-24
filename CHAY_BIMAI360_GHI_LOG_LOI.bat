@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
if not exist "BIMAI360.exe" (
  echo [ERROR] Khong tim thay BIMAI360.exe. Hay giai nen day du ZIP Portable.
  pause
  exit /b 2
)
echo [BIMAI360] Ghi loi truc tiep, KHONG su dung callback Gradio.
echo [BIMAI360] Vui long dong BIMAI360 dang chay va mo lai bang BAT nay.
echo [BIMAI360] Log: logs\console_errors.log
echo.>>"logs\console_errors.log"
echo ==== NEW LAUNCH %DATE% %TIME% ====>>"logs\console_errors.log"
"BIMAI360.exe" >>"logs\console_errors.log" 2>&1
set "APP_EXIT=%ERRORLEVEL%"
echo ==== EXIT CODE %APP_EXIT% %DATE% %TIME% ====>>"logs\console_errors.log"
echo [BIMAI360] Ung dung da dong. Exit code: %APP_EXIT%
"BIMAI360.exe" --diagnostics
echo [BIMAI360] Mo log va thu muc ZIP chan doan.
start "" notepad "logs\console_errors.log"
explorer "logs"
pause
exit /b %APP_EXIT%
