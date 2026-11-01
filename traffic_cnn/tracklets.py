"""Conservative continuity and confidence-weighted classes for vehicle tracks."""
from collections import Counter


def iou(a, b):
    intersection = max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))
    area = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection/area if area > 0 else 0


class Tracklets:
    """Link a new ID only to an unambiguous recently lost overlapping track.

    This is a heuristic, not a guarantee of physical identity. Existing raw IDs
    retain their mapping. Associations are one-to-one within each frame.
    """
    def __init__(self, max_gap=10, overlap=0.5):
        self.max_gap, self.overlap = max_gap, overlap
        self.aliases, self.state = {}, {}

    def update(self, detections, frame):
        groups = {}
        for raw,_,_,_ in detections:
            if raw in self.aliases:
                groups.setdefault(self.aliases[raw],[]).append(raw)
        for canonical,raws in groups.items():
            if len(raws) > 1:
                previous_raw = self.state.get(canonical,{}).get('raw')
                keep = canonical if canonical in raws else previous_raw if previous_raw in raws else min(raws)
                for raw in raws:
                    if raw != keep:
                        self.aliases[raw] = raw
        active = {self.aliases[d[0]] for d in detections if d[0] in self.aliases}
        candidates = {}
        for raw, box, cls, confidence in detections:
            if raw in self.aliases:
                continue
            scores = []
            for canonical, previous in self.state.items():
                gap = frame-previous['frame']
                if canonical in active or not 0 < gap <= self.max_gap:
                    continue
                prediction = [v+previous['velocity'][i]*gap for i,v in enumerate(previous['box'])]
                score = iou(box,prediction)
                if score >= self.overlap:
                    scores.append((score,canonical))
            scores.sort(reverse=True)
            if scores and (len(scores) == 1 or scores[0][0]-scores[1][0] >= 0.15):
                candidates[raw] = scores[0]
        # Reject a lost track when two new detections compete for it.
        frequency = Counter(c for _,c in candidates.values())
        output = []
        for raw, box, cls, confidence in detections:
            if raw not in self.aliases:
                candidate = candidates.get(raw)
                canonical = candidate[1] if candidate and frequency[candidate[1]] == 1 else raw
                self.aliases[raw] = canonical
            canonical = self.aliases[raw]
            previous = self.state.get(canonical)
            votes = previous['votes'] if previous else Counter()
            votes[cls] += confidence
            gap = frame-previous['frame'] if previous else 0
            velocity = [(box[i]-previous['box'][i])/gap for i in range(4)] if gap else [0]*4
            self.state[canonical] = dict(box=box,frame=frame,velocity=velocity,votes=votes,raw=raw)
            output.append((canonical,raw,box,votes.most_common(1)[0][0],confidence))
        for canonical in list(self.state):
            if frame-self.state[canonical]['frame'] > self.max_gap:
                del self.state[canonical]
        return output
