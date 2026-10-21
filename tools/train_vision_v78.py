import argparse
import json
from recognition.contextual import fit


def main():
    parser = argparse.ArgumentParser(description='V78 contextual pixel learner with grouped validation')
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--patience', type=int, default=12)
    args = parser.parse_args()
    report = fit(args.dataset, args.checkpoint, args.report, args.epochs, args.patience)
    print(json.dumps({'best_epoch': report['selected_epoch'], 'metrics': report['metrics']['test']}, indent=2))


if __name__ == '__main__':
    main()
