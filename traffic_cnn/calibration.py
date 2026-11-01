"""Planar road calibration (homography) and vehicle speed estimation.

A camera image of a flat road is related to road-plane coordinates in metres by
a 3x3 projective transform (homography). Four image points with known road
coordinates define it. Speed is then the displacement of the vehicle reference
point (bottom centre of the box) on the road plane divided by elapsed time.
The estimate assumes a flat road, a static camera and correct reference points.
"""
import json
import math
from collections import deque
from pathlib import Path
import numpy as np


def homography(source, target):
    """Direct linear transform from four (or more) point correspondences."""
    source, target = np.asarray(source, float), np.asarray(target, float)
    if source.shape != target.shape or source.ndim != 2 or source.shape[1] != 2 or len(source) < 4:
        raise ValueError('At least four 2D point correspondences are required')
    if not (np.isfinite(source).all() and np.isfinite(target).all()):
        raise ValueError('Calibration points must be finite')
    rows = []
    for (x, y), (u, v) in zip(source, target):
        rows.append([-x, -y, -1, 0, 0, 0, u*x, u*y, u])
        rows.append([0, 0, 0, -x, -y, -1, v*x, v*y, v])
    _, singular, vt = np.linalg.svd(np.asarray(rows))
    if singular[-2] < 1e-9 * singular[0]:
        raise ValueError('Calibration points are degenerate (three are collinear)')
    matrix = vt[-1].reshape(3, 3)
    if abs(matrix[2, 2]) < 1e-12:
        raise ValueError('Calibration is degenerate')
    return matrix / matrix[2, 2]


def polygon_area(points):
    p = np.asarray(points, float)
    return 0.5 * abs(np.dot(p[:, 0], np.roll(p[:, 1], 1)) - np.dot(p[:, 1], np.roll(p[:, 0], 1)))


class Calibration:
    """Image-to-road mapping. World X runs across the road, Y along it (metres)."""

    def __init__(self, image_points, world_points, lanes=None, description='', source=''):
        self.image_points = [list(map(float, p)) for p in image_points]
        self.world_points = [list(map(float, p)) for p in world_points]
        if len(self.image_points) != 4:
            raise ValueError('Exactly four image points are required')
        self.matrix = homography(self.image_points, self.world_points)
        self.inverse = np.linalg.inv(self.matrix)
        if lanes is not None and (int(lanes) != lanes or lanes < 1):
            raise ValueError('Lane count must be a positive integer')
        self.lanes = None if lanes is None else int(lanes)
        self.description, self.source = description, source
        ys = [p[1] for p in self.world_points]
        self.length_m = max(ys) - min(ys)
        self.area_m2 = polygon_area(self.world_points)
        if self.length_m <= 0 or self.area_m2 <= 0:
            raise ValueError('Calibration region must have positive length and area')

    @classmethod
    def from_rectangle(cls, image_points, width_m, length_m, **kwargs):
        """Image quadrilateral (clockwise from far-left) of a road rectangle."""
        if not (math.isfinite(width_m) and math.isfinite(length_m)) or width_m <= 0 or length_m <= 0:
            raise ValueError('Rectangle dimensions must be positive')
        return cls(image_points, [[0, 0], [width_m, 0], [width_m, length_m], [0, length_m]], **kwargs)

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data):
        extra = dict(lanes=data.get('lanes'), description=data.get('description', ''), source=data.get('source', ''))
        if 'world_points' in data:
            return cls(data['image_points'], data['world_points'], **extra)
        return cls.from_rectangle(data['image_points'], float(data['width_m']), float(data['length_m']), **extra)

    def to_dict(self):
        return dict(image_points=self.image_points, world_points=self.world_points, lanes=self.lanes,
                    length_m=self.length_m, area_m2=self.area_m2, description=self.description, source=self.source)

    def to_world(self, points):
        p = np.atleast_2d(np.asarray(points, float))
        h = np.c_[p, np.ones(len(p))] @ self.matrix.T
        return h[:, :2] / h[:, 2:3]

    def to_image(self, points):
        p = np.atleast_2d(np.asarray(points, float))
        h = np.c_[p, np.ones(len(p))] @ self.inverse.T
        return h[:, :2] / h[:, 2:3]

    def contains(self, point):
        """True when an image point lies inside the calibrated road region."""
        return point_in_polygon(point, self.image_points)

    def segment_share(self, line, samples=100):
        """Share of the counting segment x1 y1 x2 y2 that lies inside the calibrated region."""
        x1, y1, x2, y2 = line
        inside = sum(self.contains((x1+(x2-x1)*i/samples, y1+(y2-y1)*i/samples)) for i in range(samples+1))
        return inside/(samples+1)


def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


class SpeedEstimator:
    """Per-track speed from road-plane displacement over a sliding time window.

    Instantaneous frame-to-frame differences are dominated by box jitter, so the
    speed is measured over at least ``min_span`` seconds (up to ``window``) and
    the reported value is the median of recent measurements.
    """

    def __init__(self, calibration, fps, window=1.0, min_span=0.5, max_kmh=250.0, history=15):
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError('FPS must be positive')
        if not 0 < min_span <= window:
            raise ValueError('Require 0 < min_span <= window')
        self.calibration, self.fps = calibration, fps
        self.window, self.min_span, self.max_kmh = window, min_span, max_kmh
        self.history = history
        self.points, self.estimates, self.all_estimates = {}, {}, {}
        self.accepted, self.rejected = 0, 0
        self.raw = deque(maxlen=100000)  # every window measurement, including rejected ones

    def update(self, identity, point, frame, t=None):
        """Add an observation; return the current smoothed speed in km/h or None.

        ``t`` is the observation time in seconds; by default frame / fps (constant-rate video).
        Live sources pass the measured wall-clock time instead.
        """
        if not self.calibration.contains(point):
            return self.current(identity)
        t = frame / self.fps if t is None else t
        world = self.calibration.to_world(point)[0]
        track = self.points.setdefault(identity, deque())
        if track and t - track[-1][0] > self.window:
            track.clear()  # long gap: restart rather than average across it
        track.append((t, world))
        while track and t - track[0][0] > self.window:
            track.popleft()
        span = t - track[0][0]
        if span >= self.min_span:
            kmh = float(np.linalg.norm(world - track[0][1]) / span * 3.6)
            self.raw.append(kmh)
            if kmh <= self.max_kmh:
                self.accepted += 1
                self.estimates.setdefault(identity, deque(maxlen=self.history)).append(kmh)
                self.all_estimates.setdefault(identity, []).append(kmh)
            else:
                self.rejected += 1
        return self.current(identity)

    def forget(self, t):
        """Drop window and recent-estimate state of tracks not observed for longer than the window.

        The per-track medians used for the final statistics are kept.
        """
        for identity in [i for i,track in self.points.items() if not track or t-track[-1][0] > self.window]:
            del self.points[identity]
            self.estimates.pop(identity, None)

    def raw_median(self):
        """Median of all window measurements before the max_kmh filter.

        The accepted values of an accelerated video cluster just below max_kmh; the raw median
        shows how far the measured speeds really are from plausible ones.
        """
        return float(np.median(self.raw)) if self.raw else None

    def rejected_share(self):
        """Share of window measurements above max_kmh (physically implausible)."""
        total = self.accepted + self.rejected
        return self.rejected / total if total else 0.0

    def current(self, identity):
        values = self.estimates.get(identity)
        return float(np.median(values)) if values else None

    def track_speed(self, identity):
        values = self.all_estimates.get(identity)
        return float(np.median(values)) if values else None


def speed_statistics(speeds):
    """Time-mean, space-mean (harmonic), median and 85th percentile speeds."""
    values = np.asarray([s for s in speeds if s is not None and s > 0], float)
    if not len(values):
        return dict(count=0, time_mean_kmh=None, space_mean_kmh=None, median_kmh=None, p85_kmh=None, min_kmh=None, max_kmh=None)
    return dict(count=int(len(values)), time_mean_kmh=float(values.mean()), space_mean_kmh=float(len(values)/np.sum(1/values)),
                median_kmh=float(np.median(values)), p85_kmh=float(np.percentile(values, 85)),
                min_kmh=float(values.min()), max_kmh=float(values.max()))
