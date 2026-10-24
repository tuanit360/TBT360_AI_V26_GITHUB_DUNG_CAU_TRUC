@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
rem Pick only a checkpoint already validated by the shared LoRA integrity gate.
for /f "usebackq delims=" %%I in (`python -m training.select_local_lora --root loras`) do set "ADAPTER_NAME=%%I"
if not defined ADAPTER_NAME goto :missing
python -m training.local_hardware_diagnostic
if errorlevel 1 goto :fail
python -m training.verify_real_checkpoint --path "loras/%ADAPTER_NAME%"
if errorlevel 1 goto :fail
rem Unique image/report names preserve prior generations and evidence.
for /f "usebackq delims=" %%I in (`python -c "from uuid import uuid4; print(uuid4().hex[:12])"`) do set "IMAGE_RUN=%%I"
if not defined IMAGE_RUN goto :fail
python -m training.smoke_diffusers_inference --adapter "loras/%ADAPTER_NAME%" --model stable-diffusion-v1-5/stable-diffusion-v1-5 --image "loras/%ADAPTER_NAME%/image_%IMAGE_RUN%.png" --report "loras/%ADAPTER_NAME%/evidence_%IMAGE_RUN%.json" --device cuda --steps 20 --seed 42 --guidance-scale 7.5 --negative-prompt "distorted facade, extra floors, bad perspective, blurry" --prompt "Architectural photograph of a modern office building, coherent facade and window layout, daylight"
if errorlevel 1 goto :fail
python -m training.verify_inference_evidence --report "loras/%ADAPTER_NAME%/evidence_%IMAGE_RUN%.json" --image "loras/%ADAPTER_NAME%/image_%IMAGE_RUN%.png"
if errorlevel 1 goto :fail
echo [BIMAI360] Image and integrity report saved in loras/%ADAPTER_NAME%.
echo [BIMAI360] Architectural quality is NOT yet certified.
exit /b 0
:invalid
echo [BIMAI360] Invalid LoRA folder name. Use letters, digits, underscore or hyphen only.
exit /b 2
:missing
echo [BIMAI360] No verified trained checkpoint found for %ADAPTER_NAME%.
exit /b 2
:fail
echo [BIMAI360] Inference failed. Existing checkpoints and prior images were preserved.
exit /b 1
