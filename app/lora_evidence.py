"""V83 LoRA training evidence: report facts, not completion by file name."""
import hashlib
import json
from pathlib import Path


def training_evidence(root):
    folder = Path(root) / 'loras'
    results = []
    if not folder.is_dir():
        return {'verified': 0, 'runs': [], 'training_on_this_machine': False}
    for run in sorted(folder.iterdir()):
        if not run.is_dir():
            continue
        status = run / 'training_status.json'
        weights = run / 'pytorch_lora_weights.safetensors'
        item = {'name': run.name, 'checkpoint_verified': False, 'status': 'UNVERIFIED'}
        try:
            record = json.loads(status.read_text(encoding='utf-8'))
            item['status'] = record.get('status', 'UNKNOWN')
            if (record.get('status') == 'SUCCEEDED' and weights.is_file()
                    and record.get('weights_bytes') == weights.stat().st_size
                    and hashlib.sha256(weights.read_bytes()).hexdigest() == record.get('weights_sha256')):
                item['checkpoint_verified'] = True
                item['status'] = 'CHECKPOINT_SHA256_VERIFIED'
                item['sha256'] = record['weights_sha256']
            else:
                item['note'] = 'Huấn luyện chưa hoàn thành hoặc hash/size không khớp'
        except (OSError, ValueError, TypeError):
            item['note'] = 'Thiếu hoặc sai training_status.json'
        results.append(item)
    return {'verified': sum(item['checkpoint_verified'] for item in results),
            'runs': results, 'training_on_this_machine': False,
            'note': 'Đọc checkpoint có sẵn, không tự huấn luyện. Đánh giá chất lượng cần mẫu holdout và ảnh trước/sau.'}
