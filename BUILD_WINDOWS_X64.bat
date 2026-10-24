@echo off
setlocal
cd /d "%~dp0"
set "TBT360_BUILD_PROFILE=%~1"
if not defined TBT360_BUILD_PROFILE set "TBT360_BUILD_PROFILE=cpu"
if /I not "%TBT360_BUILD_PROFILE%"=="cpu" if /I not "%TBT360_BUILD_PROFILE%"=="cuda" (
  echo [ERROR] Usage: BUILD_WINDOWS_X64.bat cpu ^| cuda
  exit /b 2
)
set "PY_CMD="
where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 -c "import struct;assert struct.calcsize('P')==8" >nul 2>nul
  if not errorlevel 1 set "PY_CMD=py -3.11"
)
if not defined PY_CMD (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import sys,struct;assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8" >nul 2>nul
    if not errorlevel 1 set "PY_CMD=python"
  )
)
if not defined PY_CMD (
  echo [ERROR] Build computer needs Python 3.11 x64. Destination computer does not.
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  %PY_CMD% -m venv .venv || exit /b 1
)
set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install --upgrade pip setuptools wheel || exit /b 1
if /I "%TBT360_BUILD_PROFILE%"=="cuda" (
  "%PY%" -m pip install -r requirements.txt || exit /b 1
) else (
  "%PY%" -m pip install -r requirements-runtime.txt || exit /b 1
)
if /I "%TBT360_BUILD_PROFILE%"=="cuda" (
  "%PY%" -m pip install "torch==2.5.1" "torchvision==0.20.1" --index-url https://download.pytorch.org/whl/cu121 || exit /b 1
) else (
  "%PY%" -m pip install "torch==2.5.1" "torchvision==0.20.1" --index-url https://download.pytorch.org/whl/cpu || exit /b 1
)
"%PY%" -m pip install "pyinstaller==6.16.0" || exit /b 1
"%PY%" -m pip check || exit /b 1
"%PY%" -m unittest discover -s tests -v || exit /b 1
"%PY%" tools\build_release.py --profile "%TBT360_BUILD_PROFILE%"
exit /b %errorlevel%
