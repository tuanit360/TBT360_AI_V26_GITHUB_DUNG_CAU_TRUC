@echo off
cd /d "%~dp0"
python -m tools.recognize_v76 demo_data\v76_raster\plan.png --bounds 0 0 10 10 --reference demo_data\v76_raster\reference.json --output demo_data\v76_raster\result.json
pause
