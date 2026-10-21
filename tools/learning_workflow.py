from __future__ import annotations
import argparse
import json
from pathlib import Path
from learning.core import dataset_audit, validate_bim, geometry_score, select_checkpoint, compare_runs, append_feedback, write_json


def main():
    p = argparse.ArgumentParser(description='TBT360 V69 auditable learning gate')
    s = p.add_subparsers(dest='command', required=True)
    d=s.add_parser('audit'); d.add_argument('--manifest', type=Path, required=True); d.add_argument('--root', type=Path, required=True); d.add_argument('--out', type=Path)
    b=s.add_parser('bim'); b.add_argument('--input', type=Path, required=True)
    c=s.add_parser('checkpoints'); c.add_argument('--input', type=Path, required=True)
    q=s.add_parser('compare'); q.add_argument('--before', type=Path, required=True); q.add_argument('--after', type=Path, required=True)
    f=s.add_parser('feedback'); f.add_argument('--output', type=Path, required=True); f.add_argument('--image-sha256', required=True); f.add_argument('--project', required=True); f.add_argument('--rating', type=int, required=True); f.add_argument('--comment', default=''); f.add_argument('--consent', action='store_true')
    a=p.parse_args()
    read=lambda path: json.loads(path.read_text(encoding='utf-8'))
    if a.command=='audit': result=dataset_audit(a.manifest, a.root)
    elif a.command=='bim': result=validate_bim(read(a.input))
    elif a.command=='checkpoints': result=select_checkpoint(read(a.input))
    elif a.command=='compare': result=compare_runs(read(a.before),read(a.after))
    else: result=append_feedback(a.output, {'output_sha256':a.image_sha256,'project_id':a.project,'rating':a.rating,'comment':a.comment,'consent':a.consent})
    if getattr(a,'out',None): write_json(a.out,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result.get('status')=='BLOCKED': raise SystemExit(2)

if __name__=='__main__': main()
