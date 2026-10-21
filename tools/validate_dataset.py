from pathlib import Path
from PIL import Image, ImageOps
import argparse, hashlib, json
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
EXT={'.png','.jpg','.jpeg','.webp','.bmp'}

def validate(folder):
    folder=Path(folder)
    issues=[]
    items=[]
    hashes={}
    counts=Counter()
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in EXT:
            continue
        try:
            with Image.open(path) as img:
                img.verify()
            with Image.open(path) as img:
                width,height=img.size
            if min(width,height)<384:
                issues.append({'file':str(path),'issue':'Ảnh dưới 384 px'})
            h=hashlib.sha256(path.read_bytes()).hexdigest()
            if h in hashes:
                issues.append({'file':str(path),'issue':'Trùng nội dung với '+hashes[h]})
            hashes[h]=str(path)
            caption=path.with_suffix('.txt')
            if not caption.exists():
                issues.append({'file':str(path),'issue':'Thiếu caption riêng (sẽ dùng caption mặc định)'})
            counts[path.suffix.lower()]+=1
            items.append({'image':str(path.relative_to(folder)),'width':width,'height':height,'sha256':h,'caption_exists':caption.exists()})
        except (OSError,ValueError) as exc:
            issues.append({'file':str(path),'issue':'Ảnh lỗi: '+str(exc)})
    report={'schema':'tbt360.dataset_qa.v1','count':len(items),'by_type':dict(counts),'issues':issues,'files':items,'status':'READY' if len(items)>=5 and not any('Ảnh lỗi' in i['issue'] for i in issues) else 'NOT_READY'}
    out=ROOT/'dataset'/'validation_report.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"{report['status']}: {len(items)} ảnh, {len(issues)} cảnh báo. Báo cáo: {out}")
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--dir',default=str(ROOT/'dataset'/'raw'))
    a=p.parse_args()
    validate(a.dir)
