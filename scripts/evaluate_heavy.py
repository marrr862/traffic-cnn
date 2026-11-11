"""How much of the class error is truck/bus confusion, and what a merged "heavy vehicle" class would score.

For each test set the model predicts once; the same predictions are scored three ways:
  1. the five classes as trained (same matching and ap_per_class as Ultralytics validation);
  2. truck and bus merged into one class "heavy" in both labels and predictions;
  3. a confusion table over located vehicles: every label box matched class-agnostically (IoU >= 0.5,
     confidence >= 0.25) to the best prediction, counting which class the model gave it.

  python scripts/evaluate_heavy.py --weights runs/experiments/vehicle-road-yolov8s-long/weights/best.pt
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
from evaluate_tiled import load_labels, match  # noqa: E402
from traffic_cnn.tiling import box_iou  # noqa: E402

NAMES = ['car', 'van', 'truck', 'bus', 'motorcycle']
HEAVY = {0: 0, 1: 1, 2: 2, 3: 2, 4: 4}  # bus -> truck index, renamed "heavy"
SETS = {'visdrone': ('data/visdrone-vehicles', 960), 'mio-tcd': ('data/mio-tcd-yolo', 640)}


def score(stats, names):
    from ultralytics.utils.metrics import ap_per_class
    tp, conf, pred_cls, target_cls = (np.concatenate(x, 0) for x in zip(*stats))
    ap, classes = ap_per_class(tp, conf, pred_cls, target_cls, names=names)[5:7]
    return dict(mAP50=round(float(ap[:, 0].mean()), 4), mAP50_95=round(float(ap.mean()), 4),
                AP50={names[int(c)]: round(float(a), 4) for c, a in zip(classes, ap[:, 0])})


def main():
    from ultralytics import YOLO
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights', required=True)
    parser.add_argument('--sets', nargs='+', default=list(SETS))
    parser.add_argument('--device', default='mps')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--output', default=None)
    args = parser.parse_args()
    model = YOLO(args.weights)
    name = Path(args.weights).parents[1].name
    output = Path(args.output or ROOT/f'reports/heavy-{name}.json')
    report = dict(weights=args.weights, protocol=__doc__.strip().splitlines()[0])
    iouv = np.linspace(0.5, 0.95, 10)
    merged_names = {0: 'car', 1: 'van', 2: 'heavy', 4: 'motorcycle'}
    for key in args.sets:
        folder, imgsz = SETS[key]
        images = sorted((ROOT/folder/'images/test').glob('*.jpg'))[:args.limit or None]
        five, merged = [], []
        confusion = np.zeros((5, 6), int)  # rows: true class; columns: predicted class or missed
        for k, path in enumerate(images):
            frame = cv2.imread(str(path))
            h, w = frame.shape[:2]
            gt_boxes, gt_cls = load_labels(ROOT/folder/'labels/test'/(path.stem+'.txt'), w, h)
            r = model.predict(frame, imgsz=imgsz, conf=0.001, iou=0.7, max_det=300, device=args.device, verbose=False)[0].boxes
            boxes, scores, cls = r.xyxy.cpu().numpy(), r.conf.cpu().numpy(), r.cls.cpu().numpy().astype(int)
            five.append((match(boxes, cls, gt_boxes, gt_cls, iouv), scores, cls, gt_cls))
            mcls, mgt = np.vectorize(HEAVY.get)(cls) if len(cls) else cls, np.vectorize(HEAVY.get)(gt_cls) if len(gt_cls) else gt_cls
            merged.append((match(boxes, mcls, gt_boxes, mgt, iouv), scores, mcls, mgt))
            keep = scores >= 0.25
            kb, kc, ks = boxes[keep], cls[keep], scores[keep]
            if len(gt_boxes):
                iou = box_iou(gt_boxes, kb) if len(kb) else np.zeros((len(gt_boxes), 0))
                for g in range(len(gt_boxes)):
                    hits = np.nonzero(iou[g] >= 0.5)[0] if iou.shape[1] else []
                    if len(hits):
                        confusion[gt_cls[g], kc[hits[np.argmax(ks[hits])]]] += 1
                    else:
                        confusion[gt_cls[g], 5] += 1
            if k % 1000 == 0:
                print(key, k, len(images), flush=True)
        rows = {NAMES[t]: {**{NAMES[p]: int(confusion[t, p]) for p in range(5)}, 'missed': int(confusion[t, 5])} for t in range(5)}
        share = {NAMES[t]: {NAMES[p]: round(confusion[t, p]/max(confusion[t, :5].sum(), 1), 3) for p in range(5)} for t in range(5)}
        report[key] = dict(images=len(images), imgsz=imgsz, five_classes=score(five, dict(enumerate(NAMES))),
                           truck_bus_merged=score(merged, merged_names), located_confusion=rows, located_share=share)
        output.write_text(json.dumps(report, indent=2))
        print(key, json.dumps({k2: report[key][k2] for k2 in ('five_classes', 'truck_bus_merged')}), flush=True)
        print(key, 'truck ->', share['truck'], '| bus ->', share['bus'], flush=True)


if __name__ == '__main__':
    torch.set_grad_enabled(False)
    main()
