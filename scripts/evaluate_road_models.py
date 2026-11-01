"""Compare detectors on the drone test set (VisDrone) and the road-camera test set (MIO-TCD),
and check vehicle counting on the highway video and the UA-DETRAC sequence."""
import argparse, json, subprocess, sys
from pathlib import Path
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True, help='experiment names, comma separated')
    parser.add_argument('--sizes', default='640,960')
    parser.add_argument('--device', default='mps')
    parser.add_argument('--output', default='reports/road-model-comparison.json')
    args = parser.parse_args()
    path = ROOT/args.output
    results = json.loads(path.read_text()) if path.exists() else {}
    for name in args.models.split(','):
        weights = ROOT/'runs/experiments'/name/'weights/best.pt'
        model = YOLO(str(weights))
        entry = results.setdefault(name, {})
        for size in map(int, args.sizes.split(',')):
            for dataset, config in [('visdrone', 'configs/visdrone-vehicles.yaml'), ('mio-tcd', 'configs/mio-tcd.yaml')]:
                key = f'{dataset}@{size}'
                if key in entry:
                    continue
                r = model.val(data=str(ROOT/config), split='test', imgsz=size, batch=16, device=args.device, workers=0,
                              plots=False, verbose=False, project='/tmp/road-eval', name=f'{name}-{key}')
                entry[key] = {k: float(v) for k, v in r.results_dict.items()}
                path.write_text(json.dumps(results, indent=2))
                print(name, key, round(entry[key]['metrics/mAP50(B)'], 4), flush=True)
        # counting on the highway video (visual reference, 10 events)
        size = int(args.sizes.split(',')[-1])
        out = ROOT/f'outputs/count-{name}-{size}'
        if not (out/'summary.json').exists():
            subprocess.run([sys.executable, '-m', 'traffic_cnn.cli', 'analyze', '--video', str(ROOT/'data/video/vehicles.mp4'), '--weights', str(weights),
                            '--output', str(out), '--line', '0', '1296', '3839', '1296', '--imgsz', str(size), '--device', args.device],
                           cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        check = ROOT/f'reports/counting-{name}-{size}.json'
        if not check.exists():
            subprocess.run([sys.executable, 'scripts/evaluate_counting.py', '--results', str(out), '--name', f'{name}-{size}',
                            '--reference', 'reports/video-reference.json', '--tolerance', '6', '--output', str(check)], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        c = json.loads(check.read_text())
        entry['highway_counting'] = dict(imgsz=size, reference=c['reference_total'], predicted=c['observed_total'],
                                         matched=c['temporal_event_check']['matched_events'], f1=c['event_f1'])
        path.write_text(json.dumps(results, indent=2))
    print(json.dumps({k: {kk: (round(vv['metrics/mAP50(B)'], 4) if isinstance(vv, dict) and 'metrics/mAP50(B)' in vv else vv) for kk, vv in v.items()} for k, v in results.items()}, indent=1))


if __name__ == '__main__':
    main()
