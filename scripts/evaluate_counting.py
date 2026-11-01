"""Evaluate exported crossings using an explicit video annotation file."""
import argparse
import csv
import json
from pathlib import Path
from traffic_cnn.evaluation import match_events, evaluate_run

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--reference', default='reports/video-reference.json')
    parser.add_argument('--tolerance', type=int, default=6)
    parser.add_argument('--output')
    args = parser.parse_args()
    try:
        actual = json.loads((ROOT/args.results/'summary.json').read_text())
        reference = json.loads((ROOT/args.reference).read_text())
        with (ROOT/args.results/'crossings.csv').open() as f:
            events = list(csv.DictReader(f))
        comparison = evaluate_run(actual, reference, events, args.tolerance)
        comparison['name'] = args.name
        destination = Path(args.output) if args.output else ROOT/'reports'/f'counting-{args.name}.json'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(comparison, indent=2))
        print(json.dumps(comparison, indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
