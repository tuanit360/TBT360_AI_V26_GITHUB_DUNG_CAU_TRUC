"""Build train-only metadata from a reviewed project manifest. No hidden training data."""
import argparse
import json
from pathlib import Path
from learning.core import dataset_audit, write_json

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--prepared',type=Path,default=Path('dataset/prepared'))
    a=p.parse_args(); folder=a.prepared.resolve()
    result=dataset_audit(folder/'project_manifest.jsonl',folder)
    write_json(folder.parent/'project_split_audit.json',result)
    if result['status']!='PASS':
        raise SystemExit('BLOCKED: see project_split_audit.json')
    # Do not silently overwrite manually curated metadata.
    target=folder/'metadata.jsonl'
    if target.exists():
        target.rename(folder/'metadata_before_group_split.jsonl.bak')
    with target.open('w',encoding='utf-8') as output:
        for row in result['records']['train']:
            output.write(json.dumps({'file_name':row['file_name'],'text':row['caption']},ensure_ascii=False)+'\n')
    print(f'TRAIN projects: {result["train_projects"]}; VALIDATION projects: {result["validation_projects"]}')

if __name__=='__main__': main()
