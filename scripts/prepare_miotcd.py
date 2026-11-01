"""Convert MIO-TCD Localization (traffic surveillance cameras) to the project's five YOLO classes.

Source: https://tcd.miovision.com/ (CC BY-NC-SA 4.0). Only the 110,000 training images have
public annotations, so they are split deterministically into train / val / test here.

Class mapping (to car, van, truck, bus, motorcycle):
  car, pickup_truck -> car;  work_van -> van;  articulated_truck, single_unit_truck -> truck;
  bus -> bus;  motorcycle -> motorcycle.
  motorized_vehicle (vehicle of unknown type, occluded or far) -> painted with the image mean
  colour (ignore region) so it is neither a positive nor a false background example.
  bicycle, pedestrian, non-motorized_vehicle are not target classes and stay as background.
"""
import argparse, csv, hashlib, json, os
from collections import Counter, defaultdict
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[1]
CLASSES = {'car': 0, 'pickup_truck': 0, 'work_van': 1, 'articulated_truck': 2, 'single_unit_truck': 2, 'bus': 3, 'motorcycle': 4}
IGNORE = {'motorized_vehicle'}
NAMES = ['car', 'van', 'truck', 'bus', 'motorcycle']


def split_of(image_id, val=0.05, test=0.10):
    h = int(hashlib.sha256(image_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return 'test' if h < test else 'val' if h < test + val else 'train'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='data/mio-tcd/MIO-TCD-Localization')
    parser.add_argument('--output', default='data/mio-tcd-yolo')
    parser.add_argument('--train-subset', type=int, default=0, help='Write a list file with this many random train images (0 = all)')
    args = parser.parse_args()
    source, out = ROOT / args.source, ROOT / args.output
    boxes = defaultdict(list)
    with (source / 'gt_train.csv').open() as f:
        for image_id, label, x1, y1, x2, y2 in csv.reader(f):
            boxes[image_id].append((label, *map(float, (x1, y1, x2, y2))))
    stats = {s: Counter() for s in ('train', 'val', 'test')}
    images = {s: [] for s in stats}
    for image_id in sorted(boxes):
        split = split_of(image_id)
        src = source / 'train' / f'{image_id}.jpg'
        img = cv2.imread(str(src))
        if img is None:
            stats[split]['unreadable'] += 1
            continue
        h, w = img.shape[:2]
        lines, masked = [], False
        for label, x1, y1, x2, y2 in boxes[image_id]:
            x1, x2 = max(0, min(x1, x2)), min(w, max(x1, x2))
            y1, y2 = max(0, min(y1, y2)), min(h, max(y1, y2))
            if x2 - x1 < 1 or y2 - y1 < 1:
                stats[split]['invalid_box'] += 1
                continue
            if label in IGNORE:
                img[int(y1):int(y2), int(x1):int(x2)] = img.reshape(-1, 3).mean(0)
                masked = True
                stats[split]['masked_motorized_vehicle'] += 1
            elif label in CLASSES:
                c = CLASSES[label]
                lines.append(f'{c} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}')
                stats[split][NAMES[c]] += 1
            else:
                stats[split]['non_target_' + label] += 1
        image_dir, label_dir = out / 'images' / split, out / 'labels' / split
        image_dir.mkdir(parents=True, exist_ok=True); label_dir.mkdir(parents=True, exist_ok=True)
        dst = image_dir / f'{image_id}.jpg'
        if not dst.exists():
            if masked:
                cv2.imwrite(str(dst), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            else:
                dst.symlink_to(src.resolve())
        (label_dir / f'{image_id}.txt').write_text('\n'.join(lines) + ('\n' if lines else ''))
        images[split].append(os.path.abspath(dst))  # keep the /images/ path so YOLO finds /labels/
        stats[split]['images'] += 1
    import random
    train = sorted(images['train'])
    if args.train_subset:
        random.Random(42).shuffle(train)
        train = sorted(train[:args.train_subset])
    (out / 'train-subset.txt').write_text('\n'.join(train) + '\n')
    report = dict(source='https://tcd.miovision.com/static/dataset/MIO-TCD-Localization.tar', license='CC BY-NC-SA 4.0',
                  mapping=CLASSES, ignored_as_masked=sorted(IGNORE), split_rule='sha256(image_id): 10% test, 5% val, 85% train',
                  train_subset=len(train), splits={s: dict(c) for s, c in stats.items()},
                  limitation='MIO-TCD gives no camera identifiers; frames of the same camera can fall in different splits.')
    (ROOT / 'reports/mio-tcd-dataset.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report['splits'], indent=1))


if __name__ == '__main__':
    main()
