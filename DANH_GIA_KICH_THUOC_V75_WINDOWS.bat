@echo off
setlocal
cd /d "%~dp0"
python -m evaluation.metric_gate demo_data\v75_metric\manifest.json --assets demo_data\v75_metric --output reports\v75_metric_demo.json --tolerance-m 0.02
if errorlevel 1 exit /b 1
echo V75 metric demo completed. Synthetic test only.
