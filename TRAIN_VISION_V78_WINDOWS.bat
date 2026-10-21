@echo off
setlocal
cd /d "%~dp0"
py -3.11 -m tools.train_vision_v78 --dataset demo_data\v77_synthetic --checkpoint output\v78_demo_weights.npz --report output\v78_demo_report.json
if errorlevel 1 (echo Training failed & pause & exit /b 1)
echo Synthetic demo finished. NOT a production checkpoint.
pause
