@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\active_python.txt" (echo Thieu Python tren may build & exit /b 1)
set /p PYTHON=<"runtime\active_python.txt"
"%PYTHON%" -m evaluation.bim_plan "demo_data\canonical_office_example.json" --annotations "dataset\v74_annotations" --bounds 0 0 10 8 --width 1024 --height 768 --classes wall door window --output "reports\v74_bim_plan.json"
if errorlevel 1 (echo DANH GIA KHONG DAT: phai co nhan doc lap & exit /b 1)
echo Hoan thanh bao cao V74.
