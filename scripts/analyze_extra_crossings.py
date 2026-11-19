"""Why the original counting rules over-count on UA-DETRAC: classify every extra crossing.

ByteTrack, the 20 evaluation sequences, the original rules (start-crossing rule on, no minimum
track age); the saved tracks are replayed exactly as scripts/tune_counting_rules.py does, so the
totals match reports/DETRAC_COUNTING.md. Each unmatched predicted crossing gets the first label
that applies: motorcycle (not annotated in UA-DETRAC); start_rule (the track was never seen on the
near side of the line, so only the start-crossing rule counted it); short_track (under 10
frames); duplicate (a matched crossing in the same direction within 25 frames and about one box
width); near_unmatched_reference (an unmatched reference crossing of the same direction lies
within 50 frames: the same vehicle counted outside the 6-frame tolerance); track_under_1s;
no_reference_vehicle (no reference crossing nearby: an unannotated vehicle or a false track).

    python scripts/analyze_extra_crossings.py   ->  reports/detrac-extra-crossings.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from tune_counting_rules import DEFAULT, LINE, ignored_share, match_events, prepare, replay, test_sequences  # noqa: E402

LINE_Y = LINE[1]
data = prepare(test_sequences()[::2], 'bytetrack')
counts, total_pred, total_matched = Counter(), 0, 0
for sequence, folder, rows, frames, first, references, mask in data:
    events, boxes = replay(rows, frames, DEFAULT)
    kept = [e for e in events if ignored_share(boxes[(int(e['frame']), e['track_id'])], mask) < 0.5
            and not (first[e['track_id']][0] < 5 and (first[e['track_id']][1] > LINE_Y) == (e['direction'] == 'negative_to_positive'))]
    match = match_events(references, kept, tolerance=6)
    matched_ids = {(p['predicted']['frame'], p['predicted']['track_id']) for p in match['matched_pairs']}
    matched = [p['predicted'] for p in match['matched_pairs']]
    total_pred += len(kept)
    total_matched += len(matched)
    ys = {}
    for n, observed in rows.items():
        for row in observed:
            ys.setdefault(row['track_id'], []).append((n, float(row['y']), float(row['x']), float(row['box_width'])))
    for e in kept:
        if (e['frame'], e['track_id']) in matched_ids:
            continue
        track = sorted(ys[e['track_id']])
        after_below = e['direction'] == 'negative_to_positive'  # bottom-centre moves to larger y
        seen_before = any((y < LINE_Y - 4) if after_below else (y > LINE_Y + 4) for _, y, _, _ in track)
        frame = int(e['frame'])
        x_here = next(x for n, _, x, _ in track if n <= frame) if track else 0
        width = track[0][3] if track else 0
        if e['vehicle_class'] == 'motorcycle':
            kind = 'motorcycle'
        elif not seen_before:
            kind = 'start_rule'
        elif len(track) < 10:
            kind = 'short_track'
        elif any(m['direction'] == e['direction'] and abs(int(m['frame']) - frame) <= 25 and
                 abs(next((x for n, _, x, _ in sorted(ys[m['track_id']]) if n >= int(m['frame'])), -1e9) - x_here) < max(width, 30)
                 for m in matched):
            kind = 'duplicate'
        else:
            unmatched_refs = [r for r in references if r['direction'] == e['direction'] and
                              not any(pp['reference'] is r for pp in match['matched_pairs'])]
            near = [r for r in unmatched_refs if r['frame_interval'][0] - 50 <= frame <= r['frame_interval'][1] + 50]
            if near:
                kind = 'near_unmatched_reference'
            elif len(track) < 25:
                kind = 'track_under_1s'
            else:
                kind = 'no_reference_vehicle'
        counts[kind] += 1
report = dict(tracker='bytetrack', rules=DEFAULT, sequences='evaluation (20)', predicted=total_pred, matched=total_matched,
              extra=total_pred - total_matched, by_cause=dict(counts.most_common()), protocol=__doc__.strip().split('\n\n')[1])
(ROOT/'reports/detrac-extra-crossings.json').write_text(json.dumps(report, indent=1) + '\n')
print(json.dumps(report, indent=1))
