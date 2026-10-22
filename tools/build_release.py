"""Atomic-ish Windows release assembly, validation and SHA256 manifest."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {'output', 'logs', 'dataset', 'loras', '__pycache__'}


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(folder, profile):
    files = {}
    for path in sorted(folder.rglob('*')):
        if path.is_file() and path.name != 'SHA256SUMS.txt':
            name = path.relative_to(folder).as_posix()
            files[name] = {'bytes': path.stat().st_size, 'sha256': file_hash(path)}
    return {'schema': 'tbt360.portable.manifest.v1', 'profile': profile, 'files': files}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', choices=('cpu', 'cuda'), required=True)
    args = parser.parse_args()
    target = ROOT / 'dist' / 'BIMAI360'
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
               '--console', '--name', 'BIMAI360',
               '--collect-all', 'gradio', '--collect-all', 'gradio_client',
               '--collect-all', 'safehttpx',
               '--collect-all', 'diffusers', '--collect-all', 'transformers',
               '--collect-all', 'accelerate', '--collect-all', 'huggingface_hub',
               '--collect-all', 'safetensors', '--collect-all', 'peft',
               '--collect-all', 'torch', '--collect-all', 'torchvision',
               '--collect-all', 'PIL', '--collect-all', 'tokenizers',
               # Training-only datasets/tensorboard stay in source, not CPU EXE.
               '--collect-all', 'cv2',
               '--collect-submodules', 'app', '--collect-submodules', 'tools',
               '--collect-submodules', 'learning',
               '--hidden-import', 'multipart', '--hidden-import', 'sentencepiece',
               '--hidden-import', 'scipy', '--hidden-import', 'sklearn',
               '--hidden-import', 'aiofiles', '--hidden-import', 'uvicorn',
               '--hidden-import', 'fastapi', str(ROOT / 'run_portable.py')]
    print('[BUILD] ', ' '.join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    exe = target / 'BIMAI360.exe'
    if not exe.is_file():
        raise RuntimeError('PyInstaller did not create the executable')
    for name in ('models', 'output', 'loras', 'dataset', 'logs'):
        (target / name).mkdir(exist_ok=True)
    for model_name in ('sd15', 'sdxl', 'control_sd15', 'control_sdxl', 'x4_upscaler'):
        model = ROOT / 'models' / model_name
        if model.is_dir():
            if (model / 'model_index.json').is_file():
                shutil.copytree(model, target / 'models' / model_name, dirs_exist_ok=True)
            else:
                print(f'[WARN] {model_name} missing model_index.json; offline model not included')
    shutil.copy2(ROOT / 'README_PORTABLE.md', target / 'README_PORTABLE.md')
    shutil.copy2(ROOT / 'APP_VERSION.txt', target / 'APP_VERSION.txt')
    shutil.copy2(ROOT / 'README_START_HERE.md', target / 'README_START_HERE.md')
    shutil.copy2(ROOT / 'CHECK_PORTABLE.bat', target / 'CHECK_PORTABLE.bat')
    shutil.copy2(ROOT / 'START_BIMAI360_DIAGNOSTIC.bat', target / 'START_BIMAI360_DIAGNOSTIC.bat')
    shutil.copy2(ROOT / 'VERIFY_SHA256_WINDOWS.ps1', target / 'VERIFY_SHA256_WINDOWS.ps1')
    shutil.copy2(ROOT / 'CHAY_OFFLINE_WINDOWS.bat', target / 'CHAY_OFFLINE_WINDOWS.bat')
    result = subprocess.run([str(exe), '--self-test'], cwd=target, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(f'Frozen self-test failed with code {result.returncode}; release withheld')
    manifest = build_manifest(target, args.profile)
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    sha_lines = [f"{meta['sha256']}  {name}" for name, meta in manifest['files'].items()]
    sha_lines.append(f"{file_hash(target / 'manifest.json')}  manifest.json")
    (target / 'SHA256SUMS.txt').write_text('\n'.join(sha_lines) + '\n', encoding='utf-8')
    archive = ROOT / f'BIMAI360_V261_PORTABLE_WINDOWS_X64_{args.profile.upper()}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as dst:
        for path in sorted(target.rglob('*')):
            if path.is_file():
                dst.write(path, arcname=Path('BIMAI360') / path.relative_to(target))
    print('[OK] Created:', archive)
    print('[INFO] SHA256:', file_hash(archive))
    print('[INFO] Offline model included:', (target / 'models' / 'sd15' / 'model_index.json').is_file())


if __name__ == '__main__':
    main()
