"""Download optional models to support offline portable packaging."""
import argparse
from pathlib import Path
from huggingface_hub import snapshot_download
from app.advanced import MODEL_IDS, CONTROL_IDS, UPSCALE_ID

root = Path(__file__).resolve().parents[1] / 'models'
repos = {'sd15': MODEL_IDS['SD 1.5'], 'sdxl': MODEL_IDS['SDXL 1.0'],
         'control_sd15': CONTROL_IDS['SD 1.5'], 'control_sdxl': CONTROL_IDS['SDXL 1.0'],
         'x4_upscaler': UPSCALE_ID}
p = argparse.ArgumentParser()
p.add_argument('--models', nargs='+', choices=sorted(repos), required=True)
args = p.parse_args()
for name in args.models:
    dest = root / name
    snapshot_download(repo_id=repos[name], local_dir=str(dest))
    if not (dest / 'model_index.json').is_file():
        raise RuntimeError(f'Model download incomplete: {name}')
    print('Download verified:', name)
