import argparse
import json
from recognition.learned import train,infer

def main():
    parser=argparse.ArgumentParser(description='V77 small trainable pixel baseline')
    parser.add_argument('--dataset',required=True)
    parser.add_argument('--checkpoint',required=True)
    parser.add_argument('--epochs',type=int,default=50)
    parser.add_argument('--report',required=True)
    args=parser.parse_args()
    result=train(args.dataset,args.checkpoint,args.epochs)
    with open(args.report,'w',encoding='utf-8') as file:
        json.dump(result,file,ensure_ascii=False,indent=2)
    print(json.dumps(result['metrics'],indent=2))
if __name__=='__main__': main()
