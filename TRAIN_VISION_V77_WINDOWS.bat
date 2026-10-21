@echo off
cd /d "%~dp0"
python -m tools.train_vision_v77 --dataset demo_data\v77_synthetic --checkpoint output\v77_model.npz --report output\v77_report.json
if errorlevel 1 (echo V77 training failed & exit /b 1)
echo Synthetic demo completed. Replace with real, licensed annotations for meaningful training.
