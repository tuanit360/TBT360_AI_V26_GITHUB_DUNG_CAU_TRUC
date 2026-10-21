"""Paired before/after LoRA comparison with identical source, prompt and seeds."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image
from generate import create, installed_loras


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--lora', required=True)
    parser.add_argument('--prompt', default='contemporary sustainable office building')
    parser.add_argument('--seed', type=int, default=1234)
    args = parser.parse_args()
    if args.lora == 'Không dùng LoRA' or args.lora not in installed_loras():
        parser.error('LoRA chưa được xác minh. Hãy train thành công trước.')
    if not args.image.is_file():
        parser.error('Ảnh đầu vào không tồn tại')
    with Image.open(args.image) as image:
        image = image.convert('RGB')
        before = create(image, args.prompt, 0.45, 18, 1, args.seed,
                        'Ngang 4:3', 'Giữ đủ ảnh (thêm viền)',
                        'Tiết kiệm VRAM tối đa', 'Không dùng LoRA')
        after = create(image, args.prompt, 0.45, 18, 1, args.seed,
                       'Ngang 4:3', 'Giữ đủ ảnh (thêm viền)',
                       'Tiết kiệm VRAM tối đa', args.lora)
    print(json.dumps({'baseline_zip': before[1], 'lora_zip': after[1],
                      'seed': args.seed, 'lora': args.lora,
                      'note': 'So sánh trực quan; không tự chứng minh chất lượng kiến trúc.'},
                     ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
