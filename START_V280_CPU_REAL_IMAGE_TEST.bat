@echo off
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
if exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
  if exist ".venv-cuda\Scripts\python.exe" (
    set "PYTHON_EXE=.venv-cuda\Scripts\python.exe"
  ) else (
    echo [LOI] Can Python 3.11 VENV: .venv hoac .venv-cuda
    pause
    exit /b 2
  )
)
echo Kiem thu sinh anh SD1.5 thuc bang CPU. Can checkpoint models\sd15 day du.
set "BIMAI360_FORCE_CPU=1"
"%PYTHON_EXE%" -m tools.smoke_real_image_inference --device cpu --model-dir models/sd15 --output-dir output/v280_cpu_real_smoke > "logs\v280_cpu_smoke.log" 2>&1
set "RESULT=%ERRORLEVEL%"
type "logs\v280_cpu_smoke.log"
if "%RESULT%"=="0" echo PASS - Xem output\v280_cpu_real_smoke\real_sd15_smoke.png
if not "%RESULT%"=="0" echo FAIL - Xem logs\v280_cpu_smoke.log, khong tuyen bo tao anh thanh cong.
pause
exit /b %RESULT%
