from math import hypot, isfinite

class LineCounter:
    """Finite counting segment with hysteresis; one event per track ID.

    A track that is first seen already just past the line (closer than ``start_fraction`` of its
    box height, e.g. at the start of the video or after a late detection) is counted once it moves
    away from the line by ``away_fraction`` of its height within ``confirm_frames``. It is not counted
    when a vehicle counted in the same direction disappeared nearby just before: that is most likely
    the same vehicle under a new tracker ID.
    """
    def __init__(self, a, b, margin=4, max_gap=30, start_fraction=0.5, away_fraction=0.25, confirm_frames=15):
        if not all(isfinite(v) for v in (*a,*b,margin,max_gap,start_fraction,away_fraction,confirm_frames)):
            raise ValueError('Line and parameters must be finite')
        self.a, self.b = a, b
        self.length = hypot(b[0]-a[0], b[1]-a[1])
        if self.length == 0 or margin < 0 or max_gap < 1 or start_fraction < 0 or away_fraction <= 0 or confirm_frames < 1:
            raise ValueError('Invalid line or parameters')
        self.margin, self.max_gap = margin, max_gap
        self.start_fraction, self.away_fraction, self.confirm_frames = start_fraction, away_fraction, confirm_frames
        self.previous, self.counted, self.directions, self.started = {}, set(), {}, {}

    def update(self, identity, point, frame, size=None):
        ax, ay = self.a
        dx, dy = self.b[0]-ax, self.b[1]-ay
        distance = (dx*(point[1]-ay)-dy*(point[0]-ax))/self.length
        side = 1 if distance > self.margin else -1 if distance < -self.margin else 0
        if (identity not in self.previous and identity not in self.started and identity not in self.counted
                and size and abs(distance) <= self.start_fraction*size and self._on_segment(point)):
            self.started[identity] = (frame, distance, point, size)
        if not side:
            return None
        if identity in self.started:
            direction = self._started_crossing(identity, distance, side, frame)
            if direction:
                self.previous[identity] = (point, distance, side, frame)
                return direction
        old = self.previous.get(identity)
        self.previous[identity] = (point, distance, side, frame)
        if old is None or identity in self.counted or side == old[2] or frame-old[3] > self.max_gap:
            return None
        t = old[1]/(old[1]-distance)
        cross = tuple(old[0][i]+t*(point[i]-old[0][i]) for i in range(2))
        if not self._on_segment(cross):
            return None
        self.started.pop(identity, None)
        return self._count(identity, 'negative_to_positive' if side == 1 else 'positive_to_negative')

    def _on_segment(self, point):
        ax, ay = self.a
        dx, dy = self.b[0]-ax, self.b[1]-ay
        return 0 <= ((point[0]-ax)*dx+(point[1]-ay)*dy)/(self.length**2) <= 1

    def _count(self, identity, direction):
        self.counted.add(identity)
        self.directions[identity] = direction
        return direction

    def _started_crossing(self, identity, distance, side, frame):
        """Direction when a track first seen at the line has moved away from it, else None."""
        start_frame, start_distance, start_point, size = self.started[identity]
        if frame-start_frame > self.confirm_frames or start_distance*side < -self.margin:
            del self.started[identity]  # stayed at the line, or crossed it normally (handled below)
            return None
        if abs(distance)-max(start_distance*side,0) < self.away_fraction*size:
            return None
        del self.started[identity]
        direction = 'negative_to_positive' if side == 1 else 'positive_to_negative'
        for other in self.counted:
            last_point, _, _, last_frame = self.previous.get(other, (None,0,0,-10**9))
            if (self.directions.get(other) == direction and 0 < start_frame-last_frame <= self.max_gap
                    and hypot(last_point[0]-start_point[0], last_point[1]-start_point[1]) <= 2*size):
                return None
        return self._count(identity, direction)

    def forget(self, frame):
        """Drop side states older than max_gap: they can no longer produce an event (bounded memory on live streams)."""
        for identity in [i for i,old in self.previous.items() if frame-old[3] > self.max_gap]:
            del self.previous[identity]
        for identity in [i for i,started in self.started.items() if frame-started[0] > self.confirm_frames]:
            del self.started[identity]


def overlap_ratio(a, b):
    """Intersection over the smaller box: near 1 when one box lies inside the other."""
    w = min(a[2],b[2])-max(a[0],b[0])
    h = min(a[3],b[3])-max(a[1],b[1])
    if w <= 0 or h <= 0:
        return 0.0
    smaller = min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1]))
    return w*h/smaller if smaller > 0 else 0.0


class DuplicateGuard:
    """Rejects a crossing made by a second tracker ID of a vehicle that was already counted.

    A crossing is a duplicate when, in the same frame, its box largely coincides with the box
    of another visible ID that crossed in the same direction shortly before (for example the
    cab and the whole box of one truck). Closeness in time or position alone is not used:
    consecutive vehicles in one lane cross a few frames apart at almost the same point.
    """
    def __init__(self, overlap=0.7, window=50):
        if not 0 < overlap <= 1 or window < 1:
            raise ValueError('Invalid duplicate guard parameters')
        self.overlap, self.window = overlap, window
        self.crossed = {}

    def duplicate_of(self, identity, box, direction, frame, boxes):
        """ID of the counted vehicle this crossing duplicates, or None (then it is registered)."""
        for other,(crossed_frame,crossed_direction) in self.crossed.items():
            if (other != identity and crossed_direction == direction and frame-crossed_frame <= self.window
                    and other in boxes and overlap_ratio(box,boxes[other]) >= self.overlap):
                return other
        self.crossed[identity] = (frame,direction)
        return None

    def forget(self, frame):
        for identity in [i for i,(f,_) in self.crossed.items() if frame-f > self.window]:
            del self.crossed[identity]
