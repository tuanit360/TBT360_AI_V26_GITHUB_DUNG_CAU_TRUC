@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo CAN PYTHON BUILD ENVIRONMENT. DUNG GitHub Actions NEU MAY KHONG CO PYTHON.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 exit /b 1
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python -m PyInstaller --noconfirm --clean --onedir --windowed --name TBT360_AI --collect-all torch --collect-all torchvision main.py
if errorlevel 1 exit /b 1
echo EXE tai dist\TBT360_AI\TBT360_AI.exe
pause
