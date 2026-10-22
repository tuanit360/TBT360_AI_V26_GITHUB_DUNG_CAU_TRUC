@echo off
setlocal
cd /d "%~dp0"
if not exist BIMAI360.exe (echo [ERROR] BIMAI360.exe missing & exit /b 1)
if not exist _internal (echo [ERROR] _internal missing & exit /b 1)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0VERIFY_SHA256_WINDOWS.ps1"
if errorlevel 1 (echo [ERROR] File hashes did not match & exit /b 1)
BIMAI360.exe --self-test
if errorlevel 1 (echo [ERROR] Runtime diagnostics failed & exit /b 1)
echo [OK] Runtime imports succeeded. This is not a real image generation test.
echo [INFO] For complete checksums use Python on the build PC: python tools\verify_portable.py dist\BIMAI360
exit /b 0
