"""Command-line baseline raster recognition; no ML weights."""
import argparse
import json
from pathlib import Path
from recognition.raster import propose, compare


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('image',type=Path)
    parser.add_argument('--bounds',type=float,nargs=4,required=True)
    parser.add_argument('--category',choices=['wall','column','beam','slab'],default='wall')
    parser.add_argument('--level',type=float,default=0)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=propose(args.image,args.bounds,args.category,args.level)
    if args.reference:
        reference=json.loads(args.reference.read_text(encoding='utf-8'))
        result['comparison']=compare(result,reference)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'proposals':len(result['entities']), 'comparison':result.get('comparison'), 'output':str(args.output)},indent=2))

if __name__=='__main__':main()
