@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
rem Use a safe unique run name; avoid overwriting previous checkpoints or requiring manual edits.
for /f "usebackq delims=" %%I in (`python -c "from datetime import datetime,timezone; from uuid import uuid4; print('t600_'+datetime.now(timezone.utc).strftime('%%Y%%m%%d_%%H%%M%%S')+'_'+uuid4().hex[:6])"`) do set "RUN_NAME=%%I"
if not defined RUN_NAME goto :fail
echo [BIMAI360] Local Windows NVIDIA T600 SD1.5 + LoRA verification
echo [BIMAI360] Run name: %RUN_NAME%
python -m training.local_hardware_diagnostic
if errorlevel 1 goto :fail
python -m training.preflight_real_gpu --dataset dataset/v72_certified
if errorlevel 1 goto :fail
python -m training.run_lora --name "%RUN_NAME%" --steps 300
if errorlevel 1 goto :fail
python -m training.verify_real_checkpoint --path "loras/%RUN_NAME%"
if errorlevel 1 goto :fail
python -m training.smoke_diffusers_inference --adapter "loras/%RUN_NAME%" --model stable-diffusion-v1-5/stable-diffusion-v1-5 --image "loras/%RUN_NAME%/inference_real.png" --report "loras/%RUN_NAME%/inference_evidence.json" --device cuda --steps 25 --seed 42 --guidance-scale 7.5 --negative-prompt "warped building, extra floors, distorted windows" --prompt "Realistic photograph of modern office facade with coherent windows and floors, daylight"
if errorlevel 1 goto :fail
python -m training.verify_inference_evidence --report "loras/%RUN_NAME%/inference_evidence.json" --image "loras/%RUN_NAME%/inference_real.png"
if errorlevel 1 goto :fail
echo [BIMAI360] Pipeline completed. This does not independently certify architectural accuracy.
exit /b 0
:fail
echo [BIMAI360] Stopped after a failed stage. Read the error above; no success claimed.
exit /b 1
