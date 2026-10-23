@echo off
setlocal
cd /d "%~dp0"
set "BIMAI360_FORCE_CPU=1"
set "TBT360_OFFLINE=0"
set "BIMAI_EXE=%~dp0BIMAI360.exe"
if not exist "%BIMAI_EXE%" if exist "%~dp0BIMAI360\BIMAI360.exe" set "BIMAI_EXE=%~dp0BIMAI360\BIMAI360.exe"
if not exist "%BIMAI_EXE%" if exist "%~dp0dist\BIMAI360\BIMAI360.exe" set "BIMAI_EXE=%~dp0dist\BIMAI360\BIMAI360.exe"
if not exist "%BIMAI_EXE%" (
  echo [LOI] Khong tim thay BIMAI360.exe.
  echo Ban dang o thu muc source/scripts, hoac chua tai giai nen Portable.
  echo Hay tai ZIP Portable GitHub Actions va mo thu muc BIMAI360.
  echo Xem README_PORTABLE.md de biet huong dan.
  pause
  exit /b 2
)
echo [BIMAI360] Khoi dong CPU, khong CUDA: "%BIMAI_EXE%"
for %%I in ("%BIMAI_EXE%") do cd /d "%%~dpI"
"%BIMAI_EXE%"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo [LOI] BIMAI360 thoat voi ma %EXIT_CODE%.
  echo Nhat ky: logs\runtime_errors.log
  pause
)
exit /b %EXIT_CODE%
