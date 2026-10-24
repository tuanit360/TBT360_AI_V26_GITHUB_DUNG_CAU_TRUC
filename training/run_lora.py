from __future__ import annotations
import argparse
import json
import hashlib
import datetime
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO_URL='https://raw.githubusercontent.com/huggingface/diffusers/v0.31.0/examples/text_to_image/train_text_to_image_lora.py'
MODEL='stable-diffusion-v1-5/stable-diffusion-v1-5'

def reserve_run_directory(root: Path, name: str) -> Path:
    """Reserve a fresh run without touching existing LoRA checkpoints."""
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name):
        raise ValueError('Invalid LoRA run name')
    destination = Path(root) / 'loras' / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(exist_ok=False)
    return destination


def run(args):
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('Huấn luyện LoRA cần GPU CUDA. Không dùng CPU cho workflow này.')
    mem=torch.cuda.get_device_properties(0).total_memory/2**30
    if mem<8:
        raise RuntimeError(f'GPU chỉ có {mem:.1f} GiB VRAM. Huấn luyện SD1.5 LoRA có nguy cơ OOM; yêu cầu GPU từ 8GiB cho cấu hình thử này. Có thể chạy training/ trên máy GPU mạnh hơn rồi chép thư mục LoRA về máy này để sinh ảnh.')
    from training.gated_dataset import verify
    certified = ROOT / 'dataset' / 'v72_certified'
    certificate = verify(certified)
    prepared = certified / 'prepared'
    meta=prepared/'metadata.jsonl'
    if not meta.is_file():
        raise RuntimeError('Chưa tạo dataset/metadata.jsonl. Chạy chuẩn bị dữ liệu trước.')
    records=[json.loads(line) for line in meta.read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(records)<5 or any(not (prepared/row['file_name']).is_file() for row in records):
        raise RuntimeError('Dataset thiếu ảnh hoặc metadata không hợp lệ')
    if len({row['file_name'] for row in records}) != len(records):
        raise RuntimeError('Dataset có file_name trùng')
    if len(records) != certificate['train_count']:
        raise RuntimeError('Certified train count does not match trainer metadata')
    if not certificate['validation_projects'] or certificate['validation_count'] < 1:
        raise RuntimeError('Independent validation projects required')
    print(f'[DATASET V72] {len(records)} certified TRAIN images, {certificate["validation_count"]} holdout images; validation not passed into trainer.', flush=True)
    script=ROOT/'training'/'vendor'/'train_text_to_image_lora_v0310.py'
    script.parent.mkdir(exist_ok=True)
    if not script.is_file():
        print('Tải script huấn luyện chính thức diffusers v0.31.0 (cần Internet) ...',flush=True)
        urllib.request.urlretrieve(REPO_URL, script)
    if script.stat().st_size < 5000 or b'--pretrained_model_name_or_path' not in script.read_bytes():
        raise RuntimeError('Trainer tải về không hợp lệ; xóa file training/vendor rồi thử lại')
    if 'train_text_to_image_lora' not in script.name:
        raise RuntimeError('Trainer không hợp lệ')
    print('[TRAINER] SHA256:',hashlib.sha256(script.read_bytes()).hexdigest(),flush=True)
    # Never re-use even a failed run; its logs/partial weights remain intact.
    out=reserve_run_directory(ROOT, args.name)
    command=[sys.executable,str(script),'--pretrained_model_name_or_path',MODEL,
        '--train_data_dir',str(prepared),'--caption_column','text','--image_column','image',
        '--resolution','512','--center_crop','--random_flip','--train_batch_size','1',
        '--gradient_accumulation_steps','4','--max_train_steps',str(args.steps),
        '--learning_rate','1e-4','--lr_scheduler','constant','--lr_warmup_steps','0',
        '--checkpointing_steps','100','--mixed_precision','fp16','--rank','4',
        '--output_dir',str(out),'--seed','42','--report_to','tensorboard']
    env=os.environ.copy()
    env['HF_HOME']=str(ROOT/'models'/'hf_home')
    env['PYTORCH_CUDA_ALLOC_CONF']='expandable_segments:True'
    dataset_sha256=hashlib.sha256((certified/'certificate.json').read_bytes()).hexdigest()
    trainer_sha256=hashlib.sha256(script.read_bytes()).hexdigest()
    print('Huấn luyện LoRA thật, không dùng mô hình phân loại. Checkpoint:',out,flush=True)
    (out/'training_status.json').write_text(json.dumps({'status':'RUNNING','start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'images':len(records),'steps':args.steps,
        'dataset_certificate_sha256':dataset_sha256,
        'trainer_sha256':trainer_sha256},indent=2),encoding='utf-8')
    with (out/'training_command.json').open('w',encoding='utf-8') as f:
        json.dump({'argv':command,'source':REPO_URL,'images':len(records),'gpu_vram_gib':round(mem,2),'dataset_audit':str(certified/'certificate.json'),
            'dataset_certificate_sha256':dataset_sha256,
            'trainer_sha256':trainer_sha256},f,ensure_ascii=False,indent=2)
    log_path=out/'training_console.log'
    try:
        with log_path.open('w',encoding='utf-8',errors='replace') as log:
            proc=subprocess.Popen(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1)
            for line in proc.stdout:
                print(line,end='',flush=True)
                log.write(line)
                log.flush()
            code=proc.wait()
        if code != 0:
            raise RuntimeError(f'Trainer dừng mã {code}; xem {log_path}')
        weights=out/'pytorch_lora_weights.safetensors'
        if not weights.is_file() or weights.stat().st_size < 1024:
            raise RuntimeError('Không có trọng số LoRA hợp lệ sau huấn luyện')
        from safetensors import safe_open
        with safe_open(str(weights),framework='pt',device='cpu') as wf:
            key_count=len(wf.keys())
        if key_count==0:
            raise RuntimeError('Trọng số LoRA không chứa tensor')
        with weights.open('rb') as weight_stream:
            weights_sha256 = hashlib.file_digest(weight_stream, 'sha256').hexdigest()
        status={'status':'SUCCEEDED','images':len(records),'steps':args.steps,'base_model':MODEL,'trainer_source':REPO_URL,'weights_bytes':weights.stat().st_size,'weights_sha256':weights_sha256,'tensor_count':key_count,
            'dataset_certificate_sha256':dataset_sha256,
            'trainer_sha256':trainer_sha256}
        (out/'training_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
        print('SUCCESS LoRA:',out,flush=True)
    except Exception as exc:
        (out/'training_status.json').write_text(json.dumps({'status':'FAILED','error':str(exc)},ensure_ascii=False,indent=2),encoding='utf-8')
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--name',default='tbt360_architecture_v1')
    p.add_argument('--steps',type=int,default=300)
    args=p.parse_args()
    import re
    if not re.fullmatch('[a-zA-Z0-9_-]{1,64}',args.name):
        p.error('Tên LoRA phải gồm chữ, số, _ hoặc -')
    if not 50<=args.steps<=5000:
        p.error('steps 50..5000')
    run(args)
