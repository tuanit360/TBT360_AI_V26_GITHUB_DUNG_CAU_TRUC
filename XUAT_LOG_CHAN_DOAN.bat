@echo off
setlocal
cd /d "%~dp0"
echo BIMAI360 V271 - Xuat goi chan doan offline
if not exist "BIMAI360.exe" (
  echo KHONG TIM THAY BIMAI360.exe trong thu muc hien tai.
  pause
  exit /b 1
)
"BIMAI360.exe" --diagnostics
if errorlevel 1 (
  echo Xuat goi chan doan that bai. Kiem tra thu muc logs.
) else (
  echo Mo thu muc logs, gui file BIMAI360_V271_DIAGNOSTICS_*.zip.
)
if exist "logs" explorer "logs"
pause
