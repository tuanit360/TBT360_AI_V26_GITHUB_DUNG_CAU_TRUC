from __future__ import annotations
import argparse
import json
import hashlib
import shutil
from pathlib import Path
from PIL import Image, ImageOps

SUPPORTED={'.jpg','.jpeg','.png','.webp','.bmp'}

def prepare(source: Path, output: Path, default_caption: str) -> dict:
    source=source.resolve()
    output=output.resolve()
    if not source.is_dir():
        raise ValueError('Thư mục ảnh không tồn tại')
    if output == source or source in output.parents:
        raise ValueError('Đầu ra phải nằm ngoài thư mục ảnh đầu vào')
    images=sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED)
    if len(images)<5:
        raise ValueError('Cần ít nhất 5 ảnh; khuyến nghị tối thiểu 20–50 ảnh kiến trúc đa dạng, đúng nhãn')
    output.mkdir(parents=True,exist_ok=True)
    written=[]
    errors=[]
    seen_hashes={}
    duplicate_images=[]
    for index,path in enumerate(images):
        try:
            with Image.open(path) as original:
                im=ImageOps.exif_transpose(original).convert('RGB')
                if min(im.size)<256:
                    raise ValueError('Ảnh có cạnh ngắn dưới 256px')
                digest=hashlib.sha256(im.tobytes()).hexdigest()
                if digest in seen_hashes:
                    duplicate_images.append({'file':path.name,'duplicate_of':seen_hashes[digest]})
                    continue
                seen_hashes[digest]=path.name
                name=f'architecture_{len(written):05d}.png'
                im.save(output/name,optimize=True)
            caption_path=path.with_suffix('.txt')
            caption=caption_path.read_text(encoding='utf-8').strip() if caption_path.is_file() else default_caption
            if not caption:
                raise ValueError('Caption trống')
            written.append({'file_name':name,'text':caption,'source_file':path.name})
        except (OSError,ValueError,UnicodeError) as exc:
            errors.append({'file':path.name,'error':str(exc)})
    if len(written)<5:
        raise ValueError('Còn ít hơn 5 ảnh khác nhau hợp lệ sau kiểm tra')
    expected={row['file_name'] for row in written}
    for old in output.glob('architecture_*.png'):
        if old.name not in expected:
            old.unlink()
    with (output/'metadata.jsonl').open('w',encoding='utf-8') as f:
        for item in written:
            f.write(json.dumps({'file_name':item['file_name'],'text':item['text']},ensure_ascii=False)+'\n')
    report={'valid_images':len(written),'invalid_images':errors,'duplicate_images':duplicate_images,'unique_images':len(written),'records':written,
      'data_role':'concept_images_for_finetuning_not_verified_BIM',
      'caution':'Không có đánh giá holdout theo dự án; cần đánh giá riêng để xác nhận khả năng tổng quát hóa.',
      'source_image_count':len(images),'captions_from_files':sum((source/row['source_file']).with_suffix('.txt').is_file() for row in written)}
    (output/'prepare_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--caption',default='professional architectural photography of a contemporary office building, realistic facade, high quality')
    args=parser.parse_args()
    print(json.dumps(prepare(args.source,args.output,args.caption),ensure_ascii=False,indent=2))
