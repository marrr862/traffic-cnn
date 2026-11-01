"""Apparent vehicle motion per frame, relative to the vehicle's own box height.

Calibration-free and descriptive: in an accelerated (time-lapse) video vehicles jump a larger
share of their size between frames. The value also depends on camera angle and distance, so it
is reported to help choose a time scale, not used as an automatic accelerated-video detector.
"""
import math
import statistics


class MotionMeter:
    def __init__(self, still=0.01):
        self.still = still
        self.last, self.steps = {}, []

    def update(self, identity, point, height, frame):
        previous = self.last.get(identity)
        self.last[identity] = (frame, point)
        if previous and frame-previous[0] == 1 and height > 0:
            step = math.dist(point, previous[1])/height
            if step > self.still:  # ignore parked and queued vehicles
                self.steps.append(step)

    def forget(self, frame):
        for identity in [i for i,(f,_) in self.last.items() if frame-f > 1]:
            del self.last[identity]

    def summary(self, video_fps, time_fps):
        if not self.steps:
            return dict(samples=0, median_box_heights_per_frame=None, per_video_second=None, per_real_second=None)
        per_frame = statistics.median(self.steps)
        return dict(samples=len(self.steps), median_box_heights_per_frame=per_frame,
                    per_video_second=per_frame*video_fps, per_real_second=per_frame*time_fps)
