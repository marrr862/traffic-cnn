"""Tiled (sliced) detection for small vehicles in high-resolution or drone frames.

The frame is cut into overlapping tiles, each tile is detected at the model's input size
(so small vehicles are enlarged), an optional full-frame pass catches large vehicles, and
the boxes are merged with non-maximum suppression. Boxes clipped by an inner tile edge are
dropped when they are not the best view of the object, which removes most half-vehicles.
"""
import numpy as np


def tile_windows(width, height, tile, overlap=0.2):
    """Top-left aligned windows (x1, y1, x2, y2) covering the frame; the last row/column is snapped to the edge."""
    tile_w, tile_h = min(tile, width), min(tile, height)
    step_x = max(1, int(round(tile_w*(1-overlap))))
    step_y = max(1, int(round(tile_h*(1-overlap))))
    xs = list(range(0, max(width-tile_w, 0)+1, step_x))
    ys = list(range(0, max(height-tile_h, 0)+1, step_y))
    if xs[-1]+tile_w < width:
        xs.append(width-tile_w)
    if ys[-1]+tile_h < height:
        ys.append(height-tile_h)
    return [(x, y, x+tile_w, y+tile_h) for y in ys for x in xs]


def box_iou(a, b):
    """IoU between every box in a (N,4) and b (M,4)."""
    area_a = (a[:, 2]-a[:, 0]).clip(0)*(a[:, 3]-a[:, 1]).clip(0)
    area_b = (b[:, 2]-b[:, 0]).clip(0)*(b[:, 3]-b[:, 1]).clip(0)
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = (x2-x1).clip(0)*(y2-y1).clip(0)
    return inter/(area_a[:, None]+area_b[None, :]-inter+1e-9)


def box_ios(a, b):
    """Intersection over the smaller box: high when one box lies inside the other (a clipped half-vehicle)."""
    area_a = (a[:, 2]-a[:, 0]).clip(0)*(a[:, 3]-a[:, 1]).clip(0)
    area_b = (b[:, 2]-b[:, 0]).clip(0)*(b[:, 3]-b[:, 1]).clip(0)
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = (x2-x1).clip(0)*(y2-y1).clip(0)
    return inter/(np.minimum(area_a[:, None], area_b[None, :])+1e-9)


def merge(boxes, scores, classes, iou=0.5, ios=0.8, agnostic=True, max_det=300):
    """Greedy NMS by score; a lower-scored box is suppressed when IoU > iou or it is mostly inside a kept box (IoS > ios)."""
    if len(boxes) == 0:
        return boxes, scores, classes
    order = np.argsort(-scores)
    boxes, scores, classes = boxes[order], scores[order], classes[order]
    overlap_iou = box_iou(boxes, boxes)
    overlap_ios = box_ios(boxes, boxes) if ios else np.zeros_like(overlap_iou)
    same = np.ones_like(overlap_iou, dtype=bool) if agnostic else classes[:, None] == classes[None, :]
    suppressed = np.zeros(len(boxes), dtype=bool)
    keep = []
    for i in range(len(boxes)):
        if suppressed[i]:
            continue
        keep.append(i)
        if len(keep) >= max_det:
            break
        rest = slice(i+1, None)
        suppressed[rest] |= same[i, rest] & ((overlap_iou[i, rest] > iou) | (overlap_ios[i, rest] > ios))
    keep = np.array(keep)
    return boxes[keep], scores[keep], classes[keep]


def _predict(model, images, **kwargs):
    results = model.predict(images, verbose=False, **kwargs)
    out = []
    for r in results:
        b = r.boxes
        out.append((b.xyxy.cpu().numpy(), b.conf.cpu().numpy(), b.cls.cpu().numpy().astype(int)))
    return out


def predict_tiled(model, frame, tile=640, overlap=0.2, imgsz=960, full_frame=True, full_imgsz=None,
                  conf=0.25, iou=0.5, ios=0.8, agnostic=True, classes=None, device=None, max_det=300, batch=8,
                  edge_margin=2):
    """Detect on overlapping tiles (+ optional full frame) and merge. Returns (xyxy, conf, cls) numpy arrays."""
    height, width = frame.shape[:2]
    windows = tile_windows(width, height, tile, overlap)
    common = dict(conf=conf, iou=0.6, classes=classes, device=device, max_det=max_det, agnostic_nms=False)
    all_boxes, all_scores, all_classes = [], [], []
    if len(windows) > 1:
        crops = [frame[y1:y2, x1:x2] for x1, y1, x2, y2 in windows]
        for start in range(0, len(crops), batch):
            chunk = windows[start:start+batch]
            for (x1, y1, x2, y2), (b, s, c) in zip(chunk, _predict(model, crops[start:start+batch], imgsz=imgsz, **common)):
                if len(b) == 0:
                    continue
                # drop boxes touching an inner tile edge: the neighbouring tile (or full frame) sees them whole
                touch = np.zeros(len(b), dtype=bool)
                if x1 > 0:
                    touch |= b[:, 0] <= edge_margin
                if y1 > 0:
                    touch |= b[:, 1] <= edge_margin
                if x2 < width:
                    touch |= b[:, 2] >= (x2-x1)-edge_margin
                if y2 < height:
                    touch |= b[:, 3] >= (y2-y1)-edge_margin
                b, s, c = b[~touch], s[~touch], c[~touch]
                b = b+np.array([x1, y1, x1, y1], dtype=b.dtype)
                all_boxes.append(b); all_scores.append(s); all_classes.append(c)
    if full_frame or len(windows) <= 1:
        b, s, c = _predict(model, frame, imgsz=full_imgsz or imgsz, **common)[0]
        all_boxes.append(b); all_scores.append(s); all_classes.append(c)
    if not all_boxes:
        return np.zeros((0, 4), np.float32), np.zeros(0, np.float32), np.zeros(0, int)
    boxes = np.concatenate(all_boxes).astype(np.float32)
    scores = np.concatenate(all_scores).astype(np.float32)
    labels = np.concatenate(all_classes).astype(int)
    return merge(boxes, scores, labels, iou=iou, ios=ios, agnostic=agnostic, max_det=max_det)


class TiledTracker:
    """Tiled detection followed by the same ByteTrack used by model.track(); returns an Ultralytics Results object."""

    def __init__(self, model, tracker_yaml, tile=640, overlap=0.2, imgsz=960, full_frame=True):
        from ultralytics.trackers.byte_tracker import BYTETracker
        from ultralytics.utils import YAML, IterableSimpleNamespace
        self.model = model
        self.tracker = BYTETracker(IterableSimpleNamespace(**YAML.load(str(tracker_yaml))))
        self.tile, self.overlap, self.imgsz, self.full_frame = tile, overlap, imgsz, full_frame

    def track(self, frame, classes=None, conf=0.1, iou=0.5, agnostic=True, device=None):
        import torch
        from ultralytics.engine.results import Boxes, Results
        boxes, scores, labels = predict_tiled(self.model, frame, tile=self.tile, overlap=self.overlap, imgsz=self.imgsz,
                                              full_frame=self.full_frame, conf=conf, iou=iou, agnostic=agnostic,
                                              classes=classes, device=device)
        detections = np.concatenate([boxes, scores[:, None], labels[:, None].astype(np.float32)], 1) if len(boxes) else np.zeros((0, 6), np.float32)
        tracks = self.tracker.update(Boxes(detections, frame.shape[:2]), frame)
        data = torch.from_numpy(np.asarray(tracks[:, :7], dtype=np.float32)) if len(tracks) else torch.zeros((0, 6))
        return Results(orig_img=frame, path='', names=self.model.names, boxes=data)
