"""Counting accuracy on full UA-DETRAC test sequences and a comparison of trackers.

Images come from the Zenodo copy of UA-DETRAC (record 14030107; frames are byte-identical to the
authors' release, checked against the SHA-256 of MVI_39031), read by HTTP ranges so only the chosen
sequences are downloaded. Annotations come from the authors' DETRAC-Test-Annotations-XML.

Protocol (fixed before any result was seen):
- sequences: every second test sequence by name (20 of 40), whole length, 25 fps, 960x540;
- counting line: full width at 60% of the height (y = 324), bottom-centre of the box;
- reference: published trajectories passed through the same LineCounter (no start-crossing rule,
  unlimited gap: annotations are complete), one event per published ID;
- a predicted crossing is dropped when at least half of its box lies inside the published ignore
  regions (those vehicles are not annotated), or when its track was already past the line in the
  first 5 frames (it crossed before the sequence started; the start-crossing rule counts it, the
  reference cannot). Both rules were set on the pilot sequence MVI_39511, before the full run;
- matching: direction plus frame interval, tolerance 6 frames (traffic_cnn.evaluation.match_events);
- classes: UA-DETRAC car/van/bus map to ours, "others" (mostly trucks) maps to truck.

Usage: python scripts/evaluate_detrac_counting.py --trackers bytetrack,botsort,ocsort --device mps
Outputs: outputs/detrac-eval/<tracker>/<sequence>/, reports/detrac-counting.json, reports/DETRAC_COUNTING.md
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from download_detrac import RemoteZip  # noqa: E402
from traffic_cnn.counting import LineCounter  # noqa: E402
from traffic_cnn.evaluation import match_events  # noqa: E402

ZENODO = 'https://zenodo.org/records/14030107/files/UA-DETRAC.zip?download=1'
ANNOTATIONS = ROOT/'data/ua-detrac/archives/test-annotations.zip'
LINE = [0, 324, 959, 324]
CLASS_MAP = {'car': 'car', 'van': 'van', 'bus': 'bus', 'others': 'truck'}


def test_sequences():
    with zipfile.ZipFile(ANNOTATIONS) as archive:
        return sorted(Path(n).stem for n in archive.namelist() if n.endswith('.xml'))


def parse(xml_text):
    root = ET.fromstring(xml_text)
    ignored = [[float(b.get(k)) for k in ('left', 'top', 'width', 'height')] for b in root.findall('ignored_region/box')]
    frames = []
    for frame in root.findall('frame'):
        targets = []
        for target in frame.findall('target_list/target'):
            box, attribute = target.find('box'), target.find('attribute')
            x, y, w, h = [float(box.get(k)) for k in ('left', 'top', 'width', 'height')]
            targets.append(dict(id=int(target.get('id')), box=[x, y, x+w, y+h], kind=attribute.get('vehicle_type')))
        frames.append((int(frame.get('num'))-1, targets))
    return ignored, frames


def ignore_mask(regions):
    import numpy as np
    mask = np.zeros((540, 960), bool)
    for a, b, w, h in regions:
        mask[max(0, int(b)):int(b+h)+1, max(0, int(a)):int(a+w)+1] = True
    return mask


def ignored_share(box, mask):
    x0, y0 = max(0, int(box[0])), max(0, int(box[1]))
    x1, y1 = min(mask.shape[1], int(box[2])+1), min(mask.shape[0], int(box[3])+1)
    return float(mask[y0:y1, x0:x1].mean()) if x1 > x0 and y1 > y0 else 0.0


def reference_events(frames):
    counter = LineCounter(tuple(LINE[:2]), tuple(LINE[2:]), max_gap=10**9)
    kinds, last_frame, events = {}, {}, []
    for frame, targets in frames:
        for target in targets:
            kinds.setdefault(target['id'], Counter())[target['kind']] += 1
            box = target['box']
            direction = counter.update(target['id'], ((box[0]+box[2])/2, box[3]), frame)
            if direction:
                events.append(dict(label=f"published-track-{target['id']}", track=target['id'], direction=direction,
                                   frame_interval=[last_frame.get(target['id'], frame), frame]))
            last_frame[target['id']] = frame
    for event in events:
        event['class'] = CLASS_MAP.get(kinds[event.pop('track')].most_common(1)[0][0], 'truck')
    return events


def prefetch(remote, members):
    """Fetch the byte span holding these members in one streaming request (frames of a sequence are
    stored together), so reading them does not issue one small range request per few images."""
    import urllib.request
    infos = [remote.getinfo(m) for m in members]
    start = min(i.header_offset for i in infos)
    end = max(i.header_offset+30+len(i.orig_filename.encode())+len(i.extra)+i.compress_size for i in infos)+1024
    source = remote.fp
    request = urllib.request.Request(source.url, headers={'Range': f'bytes={start}-{min(end, source.size)-1}'})
    with urllib.request.urlopen(request, timeout=120) as response:
        if response.status != 206:
            raise ValueError('Range request refused')
        chunks = []
        while block := response.read(8*1024*1024):
            chunks.append(block)
    source.cache = (start, b''.join(chunks))


def prepare(sequence, remote):
    import cv2
    folder = ROOT/'data/ua-detrac'/sequence
    folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ANNOTATIONS) as archive:
        xml_text = archive.read(f'DETRAC-Test-Annotations-XML/{sequence}.xml')
    ignored, frames = parse(xml_text)
    video = ROOT/'data/video'/f'detrac-{sequence}-full.mp4'
    if not video.exists():
        manifest_path = folder/'manifest.json'
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        images = manifest.setdefault('images', {})
        members = sorted(n for n in remote.namelist() if n.startswith(f'UA-DETRAC/images/val/{sequence}__'))
        if not members:
            raise ValueError(f'{sequence} is not in the Zenodo archive')
        missing = [m for m in members if not (folder/m.split('__')[-1]).exists()]
        if missing:
            prefetch(remote, missing)
        for member in members:
            name = member.split('__')[-1]
            path = folder/name
            if not path.exists():
                data = remote.read(member)
                digest = hashlib.sha256(data).hexdigest()
                if name in images and images[name] != digest:
                    raise ValueError(f'{sequence}/{name} differs from the authors\' release checksum')
                path.write_bytes(data)
                images[name] = digest
        manifest.update(source='Zenodo record 14030107 (UA-DETRAC.zip, images/val)', xml_sha256=hashlib.sha256(xml_text).hexdigest())
        manifest_path.write_text(json.dumps(manifest, indent=1))
        temporary = video.with_suffix('.tmp.mp4')
        writer = cv2.VideoWriter(str(temporary), cv2.VideoWriter_fourcc(*'avc1'), 25, (960, 540))
        if not writer.isOpened():
            raise ValueError('Cannot encode video')
        for member in members:
            picture = cv2.imread(str(folder/member.split('__')[-1]))
            if picture is None or picture.shape[:2] != (540, 960):
                raise ValueError(f'Unexpected image {member}')
            writer.write(picture)
        writer.release()
        temporary.replace(video)
    return video, ignored, frames


def run(sequence, video, tracker, args):
    output = ROOT/args.outputs/tracker/sequence
    if not (output/'summary.json').exists():
        if output.exists():
            for item in output.iterdir():
                item.unlink()
        subprocess.run([sys.executable, '-m', 'traffic_cnn.cli', 'analyze', '--video', str(video), '--weights', str(ROOT/args.weights),
                        '--output', str(output), '--line', *map(str, LINE), '--imgsz', str(args.imgsz), '--device', args.device,
                        '--tracker', tracker, '--interval-seconds', '5', '--no-render'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return output


def score(output, references, ignored):
    summary = json.loads((output/'summary.json').read_text())
    with (output/'crossings.csv').open() as handle:
        predicted = list(csv.DictReader(handle))
    boxes, first = {}, {}
    with (output/'tracks.csv').open() as handle:
        for row in csv.DictReader(handle):
            x, y, w, h = (float(row[k]) for k in ('x', 'y', 'box_width', 'box_height'))
            boxes[(row['frame'], row['track_id'])] = [x-w/2, y-h, x+w/2, y]
            first.setdefault(row['track_id'], (int(row['frame']), y))
    mask = ignore_mask(ignored)
    in_ignored = [e for e in predicted if ignored_share(boxes[(e['frame'], e['track_id'])], mask) >= 0.5]
    # Already on the destination side of the line (y = 324) when the sequence starts.
    at_start = [e for e in predicted if e not in in_ignored and first[e['track_id']][0] < 5
                and (first[e['track_id']][1] > LINE[1]) == (e['direction'] == 'negative_to_positive')]
    kept = [e for e in predicted if e not in in_ignored and e not in at_start]
    match = match_events(references, kept, tolerance=6)
    pairs = match['matched_pairs']
    return dict(reference=len(references), predicted=len(kept), dropped_in_ignored_regions=len(in_ignored), dropped_at_sequence_start=len(at_start),
                matched=match['matched_events'], class_agreement=sum(p['reference']['class'] == p['predicted']['vehicle_class'] for p in pairs),
                tracked_ids=summary['tracked_ids'], duplicates_suppressed=summary['duplicate_guard']['suppressed'],
                processing_fps=summary['processing_fps'], frames=summary['frames'])


def aggregate(rows):
    total = {k: sum(r[k] for r in rows) for k in ('reference', 'predicted', 'matched', 'class_agreement', 'frames', 'tracked_ids')}
    precision = total['matched']/total['predicted'] if total['predicted'] else None
    recall = total['matched']/total['reference'] if total['reference'] else None
    errors = [abs(r['predicted']-r['reference'])/r['reference'] for r in rows if r['reference']]
    return dict(**total, precision=precision, recall=recall,
                f1=2*total['matched']/(total['reference']+total['predicted']) if total['reference']+total['predicted'] else None,
                total_count_error=(total['predicted']-total['reference'])/total['reference'] if total['reference'] else None,
                mape=sum(errors)/len(errors) if errors else None,
                class_accuracy=total['class_agreement']/total['matched'] if total['matched'] else None,
                processing_fps=total['frames']/sum(r['frames']/r['processing_fps'] for r in rows))


def markdown(report):
    lines = ['# Подсчёт на UA-DETRAC и сравнение трекеров', '',
             f"Модель {report['weights']}, вход {report['imgsz']} px; {len(report['sequences'])} тестовых последовательностей "
             f"({report['aggregate'][report['trackers'][0]]['frames']} кадров). Протокол — в начале scripts/evaluate_detrac_counting.py.", '',
             '| Трекер | Эталон | Найдено | Совпало | Precision | Recall | F1 | Ошибка общего счёта | MAPE по сценам | Точность класса | Кадр/с |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for tracker in report['trackers']:
        a = report['aggregate'][tracker]
        lines.append(f"| {tracker} | {a['reference']} | {a['predicted']} | {a['matched']} | {a['precision']:.3f} | {a['recall']:.3f} | {a['f1']:.3f} | "
                     f"{100*a['total_count_error']:+.1f}% | {100*a['mape']:.1f}% | {100*a['class_accuracy']:.1f}% | {a['processing_fps']:.1f} |")
    lines += ['', 'Ограничения: эталон выведен из опубликованных траекторий, а не из отдельной ручной разметки пересечений; '
              'класс «others» UA-DETRAC сопоставлен с truck; модель на UA-DETRAC не обучалась; один прогон на трекер.']
    return '\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--trackers', default='bytetrack,botsort,botsort-reid,ocsort,deepocsort,tracktrack')
    parser.add_argument('--sequences', help='Comma-separated names (default: every second test sequence)')
    parser.add_argument('--weights', default='runs/experiments/vehicle-road-yolov8s-long/weights/best.pt')
    parser.add_argument('--imgsz', type=int, default=960)
    parser.add_argument('--device', default='mps')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--development', action='store_true',
                        help='Use the other 20 test sequences (odd positions), kept apart for tuning counting rules')
    parser.add_argument('--outputs', default='outputs/detrac-eval',
                        help='Directory for per-run outputs; use a separate one per model, since finished runs are reused')
    parser.add_argument('--report', default='detrac-counting', help='Report name: reports/<name>.json and the Markdown table')
    args = parser.parse_args()
    sequences = args.sequences.split(',') if args.sequences else test_sequences()[1::2] if args.development else test_sequences()[::2]
    trackers = args.trackers.split(',')
    remote = None
    data = {}
    for sequence in sequences:
        if not (ROOT/'data/video'/f'detrac-{sequence}-full.mp4').exists() and remote is None:
            remote = zipfile.ZipFile(RemoteZip(ZENODO))
        data[sequence] = prepare(sequence, remote)
        print(f'prepared {sequence}', flush=True)
    if args.prepare_only:
        return
    results = {}
    for tracker in trackers:
        for sequence in sequences:
            video, ignored, frames = data[sequence]
            output = run(sequence, video, tracker, args)
            results.setdefault(tracker, {})[sequence] = score(output, reference_events(frames), ignored)
            print(f"{tracker} {sequence}: {results[tracker][sequence]}", flush=True)
    report = dict(weights=args.weights, imgsz=args.imgsz, sequences=sequences, trackers=trackers, per_sequence=results,
                  aggregate={t: aggregate(list(results[t].values())) for t in trackers},
                  protocol=__doc__.split('Protocol')[1].split('Usage')[0].strip())
    (ROOT/'reports'/f'{args.report}.json').write_text(json.dumps(report, indent=1))
    (ROOT/'reports'/f"{args.report.upper().replace('-', '_')}.md").write_text(markdown(report))
    print(markdown(report))


if __name__ == '__main__':
    main()
