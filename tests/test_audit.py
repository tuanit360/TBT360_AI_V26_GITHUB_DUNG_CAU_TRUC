import tempfile,sys,json
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_training import audit
with tempfile.TemporaryDirectory() as td:
    p=Path(td);rows=[]
    for i in range(5):
        name=f'image_{i}.png';Image.new('RGB',(256,256),(i*30,12,80)).save(p/name)
        rows.append(json.dumps({'file_name':name,'text':f'Office facade sample {i} architectural design'}))
    (p/'metadata.jsonl').write_text('\n'.join(rows),encoding='utf-8')
    report=audit(p)
    assert report['status']=='DATA_VALID_NOT_TRAINED',report
    rows.append(json.dumps({'file_name':'image_0.png','text':'Duplicate image file'}))
    (p/'metadata.jsonl').write_text('\n'.join(rows),encoding='utf-8')
    assert audit(p)['status']=='INVALID'
print('PASS dataset audit positive and duplicate negative')
