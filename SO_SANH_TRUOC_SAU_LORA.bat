@echo off
setlocal
cd /d "%~dp0"
set "PYTHON="
for /f "usebackq delims=" %%P in ("runtime\active_python.txt") do set "PYTHON=%%P"
if not exist "runtime\active_python.txt" (
 echo Chay CHAY_TBT360_AI_WINDOWS.bat truoc.
 pause
 exit /b 1
)
set /p IMAGE=Duong dan anh JPG/PNG de so sanh: 
set /p LORA=Ten LoRA da huan luyen [tbt360_architecture_v1]: 
if "%LORA%"=="" set "LORA=tbt360_architecture_v1"
"%PYTHON%" app\evaluate.py --image "%IMAGE%" --lora "%LORA%"
pause
