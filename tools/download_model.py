"""Download optional SD 1.5 model for offline inference; check model license/access."""
from pathlib import Path
from huggingface_hub import snapshot_download
root = Path(__file__).resolve().parents[1]
target = root / 'models' / 'sd15'
target.mkdir(parents=True, exist_ok=True)
snapshot_download(repo_id='stable-diffusion-v1-5/stable-diffusion-v1-5', local_dir=str(target))
assert (target / 'model_index.json').is_file(), 'Download incomplete'
print('Model downloaded to', target)
print('Run BUILD_WINDOWS_X64.bat again to include model in portable dist')
