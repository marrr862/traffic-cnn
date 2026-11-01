"""Compare full-frame and tiled detection on the VisDrone vehicle split with one evaluator.

The same metric code as Ultralytics validation is used (IoU matching at 0.50:0.95 and ap_per_class),
so the full-frame row is the reference and only the inference method changes. Settings are chosen on
the validation split; the test split is evaluated once with the chosen settings.

  python scripts/evaluate_tiled.py --split val --weights runs/experiments/vehicle-road-yolov8s/weights/best.pt \
      --configs full:960 tile:640:0.2:960:full tile:640:0.2:640:full
"""
import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from traffic_cnn.tiling import box_iou, predict_tiled  # noqa: E402


def load_labels(label_path, width, height):
    if not label_path.exists():
        return np.zeros((0, 4)), np.zeros(0, int)
    rows = [list(map(float, line.split())) for line in label_path.read_text().splitlines() if line.strip()]
    if not rows:
        return np.zeros((0, 4)), np.zeros(0, int)
    a = np.array(rows)
    cx, cy, w, h = a[:, 1]*width, a[:, 2]*height, a[:, 3]*width, a[:, 4]*height
    return np.stack([cx-w/2, cy-h/2, cx+w/2, cy+h/2], 1), a[:, 0].astype(int)


def match(pred_boxes, pred_cls, gt_boxes, gt_cls, iouv):
    """Same greedy matching as ultralytics BaseValidator.match_predictions."""
    correct = np.zeros((len(pred_boxes), len(iouv)), bool)
    if len(pred_boxes) == 0 or len(gt_boxes) == 0:
        return correct
    iou = box_iou(gt_boxes, pred_boxes)*(gt_cls[:, None] == pred_cls[None, :])
    for i, threshold in enumerate(iouv):
        matches = np.array(np.nonzero(iou >= threshold)).T
        if matches.shape[0]:
            if matches.shape[0] > 1:
                matches = matches[iou[matches[:, 0], matches[:, 1]].argsort()[::-1]]
                matches = matches[np.unique(matches[:, 1], return_index=True)[1]]
                matches = matches[np.unique(matches[:, 0], return_index=True)[1]]
            correct[matches[:, 1].astype(int), i] = True
    return correct


def parse(config):
    parts = config.split(':')
    if parts[0] == 'full':
        return dict(name=config, tile=None, imgsz=int(parts[1]))
    tile, overlap, imgsz = int(parts[1]), float(parts[2]), int(parts[3])
    return dict(name=config, tile=tile, overlap=overlap, imgsz=imgsz, full_frame=len(parts) > 4 and parts[4] == 'full',
                full_imgsz=int(parts[5]) if len(parts) > 5 else None)


def main():
    from ultralytics import YOLO
    from ultralytics.utils.metrics import ap_per_class
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', required=True)
    parser.add_argument('--data', default=str(ROOT/'data/visdrone-vehicles'))
    parser.add_argument('--split', default='val')
    parser.add_argument('--configs', nargs='+', default=['full:960', 'tile:640:0.2:960:full'])
    parser.add_argument('--device', default='mps')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--agnostic', action='store_true', help='class-agnostic merge (the video pipeline default)')
    parser.add_argument('--output', default=None)
    args = parser.parse_args()
    model = YOLO(args.weights)
    images = sorted((Path(args.data)/'images'/args.split).glob('*.jpg'))
    if args.limit:
        images = images[:args.limit]
    iouv = np.linspace(0.5, 0.95, 10)
    output = Path(args.output or ROOT/f'reports/tiled-{Path(args.weights).parents[1].name}-{args.split}.json')
    report = json.loads(output.read_text()) if output.exists() else {}
    for config in map(parse, args.configs):
        key = config['name']+(':agnostic' if args.agnostic else '')
        if key in report:
            print(key, 'cached', report[key]['mAP50'], flush=True)
            continue
        stats, start = [], time.perf_counter()
        for k, image_path in enumerate(images):
            frame = cv2.imread(str(image_path))
            height, width = frame.shape[:2]
            gt_boxes, gt_cls = load_labels(Path(args.data)/'labels'/args.split/(image_path.stem+'.txt'), width, height)
            if config['tile'] is None:
                r = model.predict(frame, imgsz=config['imgsz'], conf=0.001, iou=0.7, max_det=300, device=args.device,
                                  agnostic_nms=args.agnostic, verbose=False)[0].boxes
                boxes, scores, cls = r.xyxy.cpu().numpy(), r.conf.cpu().numpy(), r.cls.cpu().numpy().astype(int)
            else:
                boxes, scores, cls = predict_tiled(model, frame, tile=config['tile'], overlap=config['overlap'], imgsz=config['imgsz'],
                                                   full_frame=config['full_frame'], full_imgsz=config['full_imgsz'], conf=0.001,
                                                   iou=0.6, ios=0.8, agnostic=args.agnostic, device=args.device, max_det=300)
            stats.append((match(boxes, cls, gt_boxes, gt_cls, iouv), scores, cls, gt_cls))
            if k % 200 == 0:
                print(key, k, len(images), flush=True)
        seconds = time.perf_counter()-start
        tp, conf, pred_cls, target_cls = (np.concatenate(x, 0) for x in zip(*stats))
        result = ap_per_class(tp, conf, pred_cls, target_cls, names=model.names)
        ap, classes = result[5], result[6]
        report[key] = dict(mAP50=round(float(ap[:, 0].mean()), 4), mAP50_95=round(float(ap.mean()), 4),
                           per_class_AP50={model.names[int(c)]: round(float(a), 4) for c, a in zip(classes, ap[:, 0])},
                           images=len(images), ms_per_image=round(1000*seconds/len(images), 1),
                           split=args.split, weights=str(Path(args.weights).relative_to(ROOT)) if Path(args.weights).is_absolute() and ROOT in Path(args.weights).parents else args.weights)
        output.write_text(json.dumps(report, indent=2))
        print(key, report[key]['mAP50'], report[key]['mAP50_95'], report[key]['ms_per_image'], 'ms', flush=True)


if __name__ == '__main__':
    torch.set_grad_enabled(False)
    main()
