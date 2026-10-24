@echo off
setlocal
cd /d "%~dp0"
echo BIMAI360 V271 - Chan doan GPU va model
echo === GPU NVIDIA (neu co) ===
where nvidia-smi >nul 2>&1
if not errorlevel 1 nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
if errorlevel 1 echo Khong tim thay nvidia-smi; co the may khong co NVIDIA hoac chua cai driver.
echo.
echo === CPU / RAM ===
powershell -NoProfile -Command "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name; Get-CimInstance Win32_ComputerSystem | ForEach-Object { 'RAM_GB: ' + [math]::Round($_.TotalPhysicalMemory/1GB,1) }"
echo.
echo === Model SD1.5 ===
if exist "models\sd15\model_index.json" (echo model_index.json: CO) else (echo model_index.json: THIEU)
for %%D in (unet vae text_encoder tokenizer scheduler) do (
  if exist "models\sd15\%%D\" (echo %%D: CO) else (echo %%D: THIEU)
)
echo.
echo === Goi chan doan offline ===
if exist "BIMAI360.exe" "BIMAI360.exe" --diagnostics
echo.
echo Neu can gui ho tro, mo thu muc logs va xem ZIP truoc khi chia se.
pause
