"""Run the final video analyses for the thesis and collect tables and figures.

Usage: python scripts/thesis_video_results.py --weights <best.pt> --imgsz 960 --device mps
Outputs: outputs/thesis-*/ result folders, reports/thesis/video_results.json and figures.
"""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/thesis'
VIDEOS = [
    dict(key='v1', video='data/video/vehicles.mp4', calibration='configs/calibration-vehicles.json',
         line=[0, 1296, 3839, 1296], extra=[0, 1700, 3839, 1700]),
    dict(key='v2', video='data/video/vehicles-2.mp4', calibration='configs/calibration-vehicles-2.json',
         line=[380, 860, 890, 860], extra=None),
]


def run(spec, weights, imgsz, device, tag):
    out = ROOT / f"outputs/thesis-{spec['key']}-{tag}"
    if not (out / 'summary.json').exists():
        command = [sys.executable, '-m', 'traffic_cnn.cli', 'analyze', '--video', str(ROOT / spec['video']), '--weights', str(weights),
                   '--output', str(out), '--line', *map(str, spec['line']), '--calibration', str(ROOT / spec['calibration']),
                   '--imgsz', str(imgsz), '--device', device, '--conf', '0.3', '--interval-seconds', '5']
        if spec['extra']:
            command += ['--extra-line', *map(str, spec['extra'])]
        subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return out


def read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def two_line_check(result):
    crossings = read_csv(result / 'line_crossings.csv')
    tracks = read_csv(result / 'tracks.csv')
    position = {(r['track_id'], r['frame']): (r['world_x_m'], r['world_y_m']) for r in tracks}
    summary = json.loads((result / 'summary.json').read_text())
    fps = summary['source_fps']
    by_track = {}
    for c in crossings:
        by_track.setdefault(c['track_id'], {})[c['line_id']] = c
    medians = {r['track_id']: r['median_speed_kmh'] for r in read_csv(result / 'tracks_summary.csv')}
    rows = []
    for track, lines in by_track.items():
        if '0' in lines and '1' in lines:
            a, b = lines['0'], lines['1']
            pa, pb = position.get((track, a['frame'])), position.get((track, b['frame']))
            if not pa or not pb or '' in pa + pb:
                continue
            distance = float(np.hypot(float(pa[0]) - float(pb[0]), float(pa[1]) - float(pb[1])))
            dt = abs(int(b['frame']) - int(a['frame'])) / fps
            if dt <= 0:
                continue
            two_line = distance / dt * 3.6
            median = float(medians[track]) if medians.get(track) not in (None, '') else None
            rows.append(dict(track=track, vehicle_class=a['vehicle_class'], distance_m=distance, seconds=dt, two_line_kmh=two_line, window_kmh=median))
    return rows


def snapshot(result, frame_index, name):
    cap = cv2.VideoCapture(str(result / 'annotated.mp4'))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    if ok:
        if frame.shape[1] > 1920:
            frame = cv2.resize(frame, (1920, round(frame.shape[0] * 1920 / frame.shape[1])))
        cv2.imwrite(str(OUT / name), frame, [cv2.IMWRITE_JPEG_QUALITY, 88])


def calibration_figure():
    from traffic_cnn.calibration import Calibration
    tiles = []
    for spec in VIDEOS:
        cap = cv2.VideoCapture(str(ROOT / spec['video']))
        ok, frame = cap.read()
        cap.release()
        cal = Calibration.load(ROOT / spec['calibration'])
        scale = max(1, frame.shape[1] // 960)
        cv2.polylines(frame, [np.array(cal.image_points, np.int32)], True, (255, 255, 0), 3 * scale)
        for line, color in [(spec['line'], (0, 255, 255)), (spec['extra'], (255, 0, 255))]:
            if line:
                cv2.line(frame, tuple(map(int, line[:2])), tuple(map(int, line[2:])), color, 3 * scale)
        tiles.append(cv2.resize(frame, (960, 540)))
    cv2.imwrite(str(OUT / 'calibration-zones.jpg'), np.hstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 90])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', required=True)
    parser.add_argument('--imgsz', type=int, default=960)
    parser.add_argument('--device', default='mps')
    parser.add_argument('--tag', default='final')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for spec in VIDEOS:
        result = run(spec, ROOT / args.weights, args.imgsz, args.device, args.tag)
        summary = json.loads((result / 'summary.json').read_text())
        results[spec['key']] = dict(directory=str(result.relative_to(ROOT)), summary=summary,
                                    windows=read_csv(result / 'flow_windows.csv'),
                                    track_speeds=[float(r['median_speed_kmh']) for r in read_csv(result / 'tracks_summary.csv') if r['median_speed_kmh'] not in ('', None)])
        if spec['extra']:
            results[spec['key']]['two_line'] = two_line_check(result)
        peak = max(read_csv(result / 'frame_stats.csv'), key=lambda r: int(r['visible_tracked_vehicles']))
        snapshot(result, int(peak['frame']), f"annotated-{spec['key']}.jpg")
        for name in ['heatmap.png', 'trajectories.png']:
            image = cv2.imread(str(result / name))
            if image is not None:
                if image.shape[1] > 1920:
                    image = cv2.resize(image, (1920, round(image.shape[0] * 1920 / image.shape[1])))
                cv2.imwrite(str(OUT / f"{name.split('.')[0]}-{spec['key']}.jpg"), image, [cv2.IMWRITE_JPEG_QUALITY, 88])
    calibration_figure()
    (OUT / 'video_results.json').write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print(json.dumps({k: dict(crossings=v['summary']['crossings'], speed=v['summary'].get('speed', {}).get('at_counting_line'),
                              density=v['summary'].get('density'), fps=v['summary']['processing_fps']) for k, v in results.items()}, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
