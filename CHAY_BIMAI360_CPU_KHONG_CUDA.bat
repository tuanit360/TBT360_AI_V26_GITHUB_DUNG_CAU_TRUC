@echo off
setlocal
cd /d "%~dp0"
set "BIMAI360_FORCE_CPU=1"
set "TBT360_OFFLINE=0"
echo BIMAI360 V271: che do CPU khong su dung CUDA.
echo CPU diffusion co the rat cham. Model SD1.5 phai ton tai trong cache hoac co mang.
"BIMAI360.exe"
if errorlevel 1 (
  echo Loi khi chay BIMAI360. Mo MO_LOG_KHONG_CAN_UI.bat de lay log.
  pause
)
