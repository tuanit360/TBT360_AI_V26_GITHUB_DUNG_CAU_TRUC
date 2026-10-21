from __future__ import annotations
import argparse, json, hashlib, sys
from collections import Counter
from pathlib import Path
from PIL import Image

def audit(prepared: Path):
    report={'schema':'tbt360.training_audit.v1','status':'INVALID','images':0,'caption_count':0,'bad':[],'warnings':[], 'pixel_sha256_duplicates':[], 'near_duplicate_pairs':[], 'disclosure':'Ảnh không có BIM ground truth. Đây chỉ là LoRA sinh phối cảnh; chưa chứng minh tổng quát hóa hoặc chất lượng.'}
    meta=prepared/'metadata.jsonl'
    if not meta.is_file():
        report['bad'].append('Không có metadata.jsonl');return report
    rows=[]; digests={}; captions=[]; perceptual=[]
    for i,line in enumerate(meta.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip():continue
        try:
            row=json.loads(line); name=row['file_name']; caption=row['text']
            if not isinstance(name,str) or Path(name).name!=name or not name.lower().endswith(('.png','.jpg','.jpeg','.webp')):raise ValueError('Tên ảnh không hợp lệ')
            if not isinstance(caption,str) or len(caption.strip())<12:raise ValueError('Caption dưới 12 ký tự')
            p=prepared/name
            with Image.open(p) as im:
                im.load()
                if min(im.size)<256:raise ValueError('Ảnh quá nhỏ')
                digest=hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()
                tiny=im.convert('L').resize((9,8),Image.Resampling.LANCZOS)
                values=list(tiny.getdata())
                phash=sum((1<< (y*8+x)) for y in range(8) for x in range(8) if values[y*9+x]>values[y*9+x+1])
                for former, other in perceptual:
                    if (phash ^ former).bit_count()<=5:
                        report['near_duplicate_pairs'].append([name,other])
                perceptual.append((phash,name))
            if digest in digests:report['pixel_sha256_duplicates'].append([name,digests[digest]])
            digests[digest]=name; captions.append(caption.strip());rows.append(row)
        except (KeyError,ValueError,OSError,TypeError) as e:report['bad'].append({'line':i,'reason':str(e)})
    report['images']=len(rows);report['caption_count']=len(set(captions))
    if report['images']<10:report['warnings'].append('Dưới 10 ảnh: rất dễ overfit. Nên dùng ảnh đa dạng, có caption đúng nội dung.')
    if report['caption_count']==1:report['warnings'].append('Tất cả ảnh có cùng caption: khó kiểm soát đặc điểm công trình qua prompt.')
    if report['pixel_sha256_duplicates']:report['bad'].append('Ảnh trùng nội dung sau chuẩn hóa')
    if report['near_duplicate_pairs']:report['warnings'].append('Có ảnh gần trùng về cấu trúc thị giác: kiểm tra tránh overfit và rò rỉ tập validation')
    if report['images']>=5 and not report['bad']:report['status']='DATA_VALID_NOT_TRAINED'
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=audit(a.prepared);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['status']=='DATA_VALID_NOT_TRAINED' else 2)
