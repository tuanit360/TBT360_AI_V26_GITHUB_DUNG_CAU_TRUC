@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\active_python.txt" (
 echo Chua co Python build machine. Hay cai dat moi truong tren may build.
 exit /b 1
)
set /p MANIFEST=Duong dan manifest JSON V73: 
set /p ASSETS=Thu muc assets danh gia: 
set /p REPORT=Duong dan bao cao JSON [reports\v73_evaluation.json]: 
if "%REPORT%"=="" set "REPORT=reports\v73_evaluation.json"
set /p PYTHON=<"runtime\active_python.txt"
"%PYTHON%" -m evaluation.paired_gate "%MANIFEST%" --assets "%ASSETS%" --output "%REPORT%"
if errorlevel 1 (echo DANH GIA THAT BAI & exit /b 1)
echo Xong. Bao cao: %REPORT%
