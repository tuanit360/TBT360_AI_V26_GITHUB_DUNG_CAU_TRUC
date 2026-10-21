from pathlib import Path
import sys, json, shutil
ROOT=Path(__file__).resolve().parents[1]
print('TBT360 AI V56 - Kiem tra truoc khi sinh anh')
print('Python:',sys.version.split()[0])
print('Disk free GB:',round(shutil.disk_usage(ROOT).free/2**30,2))
try:
 import torch
 print('Torch:',torch.__version__,'CUDA:',torch.cuda.is_available())
 if torch.cuda.is_available():
  p=torch.cuda.get_device_properties(0)
  print('GPU:',p.name,'VRAM GiB:',round(p.total_memory/2**30,2))
  if p.total_memory/2**30<8:print('WARN: Khong du VRAM theo nguong trainer LoRA V56 (>= 8 GiB).')
 from diffusers import AutoPipelineForImage2Image
 print('Diffusers import: OK')
except Exception as e:
 print('LOI:',repr(e))
print('Luu y: tien kiem khong thay the test sinh anh that.')
