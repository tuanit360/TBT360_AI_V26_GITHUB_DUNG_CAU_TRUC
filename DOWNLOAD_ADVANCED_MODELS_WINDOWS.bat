@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo [ERROR] Build environment .venv missing & exit /b 1)
".venv\Scripts\python.exe" -m tools.download_advanced_models --models sdxl control_sd15 control_sdxl x4_upscaler
