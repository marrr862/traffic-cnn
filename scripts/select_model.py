"""Choose the recommended road-camera model on validation only.

Candidates are the completed runs trained on the same data configuration (by default the
road-camera mix VisDrone + MIO-TCD, configs/combined-road.yaml), so their validation split is the
same and their validation mAP50-95 is directly comparable. Test metrics and the external checks
(UA-DETRAC, highway video) are copied into the record for reporting only; they play no part in
the choice. The inference size comes from the resolution study, which was also chosen on
validation (reports/RESOLUTION_RESULTS.md).

Usage: python scripts/select_model.py [--data combined-road.yaml] [--imgsz 960]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = 'metrics/mAP50-95(B)'


def candidates(data):
    runs = [json.loads(p.read_text()) for p in sorted((ROOT/'reports').glob('vehicle-*.json'))]
    return [r for r in runs if Path(r['data']).name == data and r.get('validation') and r.get('test')]


def select(runs):
    if not runs:
        raise ValueError('No completed runs on this data configuration')
    return max(runs, key=lambda r: r['validation'][KEY])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', default='combined-road.yaml')
    parser.add_argument('--imgsz', type=int, default=960)
    parser.add_argument('--output', default='reports/recommended-model.json')
    args = parser.parse_args()
    runs = candidates(args.data)
    best = select(runs)
    path = ROOT/args.output
    previous = json.loads(path.read_text()) if path.exists() else {}
    ranking = sorted(runs, key=lambda r: -r['validation'][KEY])
    record = dict(
        name=best['name'], weights=f"runs/experiments/{best['name']}/weights/best.pt", inference_imgsz=args.imgsz,
        previous=previous.get('name') if previous.get('name') != best['name'] else previous.get('previous'),
        selection_rule=f"Highest validation mAP50-95 among runs trained on {args.data} (same validation split); test and external checks not used.",
        validation_ranking=[dict(name=r['name'], validation_mAP50=r['validation']['metrics/mAP50(B)'], validation_mAP50_95=r['validation'][KEY]) for r in ranking],
        reported_test=dict(mAP50=best['test']['metrics/mAP50(B)'], mAP50_95=best['test'][KEY], note='Reported once after selection.'),
        selection=('Chosen on validation: ' + ', '.join(f"{r['name']} {100*r['validation'][KEY]:.1f}%" for r in ranking)
                   + f' mAP50-95 on the {args.data} validation split. Weights: v1.0 GitHub release (scripts/download_assets.py).'))
    path.write_text(json.dumps(record, indent=1))
    print(json.dumps(record, indent=1))


if __name__ == '__main__':
    main()
