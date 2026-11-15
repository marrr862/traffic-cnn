"""Choose the counting rules on the UA-DETRAC development sequences and report them once on the evaluation sequences.

The detector and tracker are not run again: the saved tracks (tracks.csv of each analysis) are fed
frame by frame through LineCounter and DuplicateGuard exactly as traffic_cnn.cli does, so many rule
variants can be compared in seconds. The default variant must reproduce the saved crossings.csv.

Development set: the odd-position test sequences (evaluate_detrac_counting.py --development).
Evaluation set: the even-position ones, used only for the final report of the chosen rules.
Motorcycles are left out of the comparison: UA-DETRAC does not annotate two-wheelers.

Usage: python scripts/tune_counting_rules.py
Outputs: reports/counting-rules.json, reports/COUNTING_RULES.md
"""
from collections import Counter
import csv
import itertools
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from evaluate_detrac_counting import ANNOTATIONS, LINE, aggregate, ignore_mask, ignored_share, parse, reference_events, test_sequences  # noqa: E402
from traffic_cnn.counting import DuplicateGuard, LineCounter  # noqa: E402
from traffic_cnn.evaluation import match_events  # noqa: E402

DEFAULT = dict(start_crossings=True, jump_fraction=None, min_age=1)
GRID = [dict(start_crossings=s, jump_fraction=j, min_age=a)
        for s, j, a in itertools.product((True, False), (None, 0.3, 0.5, 0.75), (1, 3, 5, 10))]
TRACKERS = ('bytetrack', 'botsort', 'botsort-reid', 'ocsort', 'deepocsort', 'tracktrack')


def load(folder):
    rows = {}
    with (folder/'tracks.csv').open() as handle:
        for row in csv.DictReader(handle):
            rows.setdefault(int(row['frame']), []).append(row)
    summary = json.loads((folder/'summary.json').read_text())
    return rows, summary['frames']


def replay(rows, frames, rules):
    """Crossings of the main line, as traffic_cnn.cli produces them, with class voted over each track."""
    counter, guard = LineCounter(tuple(LINE[:2]), tuple(LINE[2:]), **rules), DuplicateGuard()
    votes, events, boxes = {}, [], {}
    for n in range(frames):
        observed = rows.get(n, [])
        frame_boxes = {}
        for row in observed:
            x, y, w, h = (float(row[k]) for k in ('x', 'y', 'box_width', 'box_height'))
            frame_boxes[row['track_id']] = boxes[(n, row['track_id'])] = [x-w/2, y-h, x+w/2, y]
        for row in observed:
            identity, box = row['track_id'], frame_boxes[row['track_id']]
            votes.setdefault(identity, Counter())[row['vehicle_class']] += float(row['confidence'])
            direction = counter.update(identity, (float(row['x']), float(row['y'])), n, size=box[3]-box[1])
            if direction and guard.duplicate_of(identity, box, direction, n, frame_boxes) is not None:
                direction = None
            if direction:
                events.append(dict(frame=str(n), track_id=identity, direction=direction))
        if n % 100 == 0:
            counter.forget(n)
            guard.forget(n)
    for event in events:
        event['vehicle_class'] = votes[event['track_id']].most_common(1)[0][0]
    return events, boxes


def score(events, boxes, first, references, mask):
    kept = [e for e in events if e['vehicle_class'] != 'motorcycle'
            and ignored_share(boxes[(int(e['frame']), e['track_id'])], mask) < 0.5
            and not (first[e['track_id']][0] < 5 and (first[e['track_id']][1] > LINE[1]) == (e['direction'] == 'negative_to_positive'))]
    match = match_events(references, kept, tolerance=6)
    return dict(reference=len(references), predicted=len(kept), matched=match['matched_events'],
                class_agreement=sum(p['reference']['class'] == p['predicted']['vehicle_class'] for p in match['matched_pairs']),
                frames=1, processing_fps=1, tracked_ids=0)


def prepare(sequences, tracker):
    data = []
    for sequence in sequences:
        folder = ROOT/'outputs/detrac-eval'/tracker/sequence
        ignored, frames = parse(zipfile.ZipFile(ANNOTATIONS).read(f'DETRAC-Test-Annotations-XML/{sequence}.xml'))
        rows, count = load(folder)
        first = {}
        for n in sorted(rows):
            for row in rows[n]:
                first.setdefault(row['track_id'], (n, float(row['y'])))
        data.append((sequence, folder, rows, count, first, reference_events(frames), ignore_mask(ignored)))
    return data


def evaluate(data, rules):
    results = []
    for _, _, rows, count, first, references, mask in data:
        events, boxes = replay(rows, count, rules)
        results.append(score(events, boxes, first, references, mask))
    summary = aggregate(results)
    return {k: summary[k] for k in ('reference', 'predicted', 'matched', 'precision', 'recall', 'f1', 'total_count_error', 'mape', 'class_accuracy')}


def check_replay(data):
    """The default rules must give the crossings that the analysis itself saved."""
    for sequence, folder, rows, count, *_ in data:
        events, _ = replay(rows, count, DEFAULT)
        with (folder/'crossings.csv').open() as handle:
            saved = [(e['frame'], e['track_id'], e['direction']) for e in csv.DictReader(handle)]
        if sorted((e['frame'], e['track_id'], e['direction']) for e in events) != sorted(saved):
            raise ValueError(f'Replay differs from the saved crossings in {sequence}')


def label(rules):
    return (f"start {'on' if rules['start_crossings'] else 'off'}, jump "
            f"{rules['jump_fraction'] if rules['jump_fraction'] else 'off'}, min age {rules['min_age']}")


def main():
    development = prepare(test_sequences()[1::2], 'bytetrack')
    check_replay(development)
    grid = [dict(rules=rules, development=evaluate(development, rules)) for rules in GRID]
    # Best development F1; on ties the simpler rule set (fewer guards switched on) wins.
    complexity = lambda r: (r['start_crossings'], r['jump_fraction'] is not None, r['min_age'] > 1)
    best = max(grid, key=lambda g: (round(g['development']['f1'], 4), -sum(complexity(g['rules']))))
    chosen = best['rules']
    evaluation = {}
    for tracker in TRACKERS:
        data = prepare(test_sequences()[::2], tracker)
        check_replay(data)
        evaluation[tracker] = dict(default=evaluate(data, DEFAULT), chosen=evaluate(data, chosen))
    report = dict(chosen=chosen, chosen_label=label(chosen), default=DEFAULT, grid=grid, evaluation=evaluation,
                  protocol=__doc__.split('Usage')[0].strip())
    (ROOT/'reports/counting-rules.json').write_text(json.dumps(report, indent=1))
    lines = ['# Правила подсчёта: выбор на UA-DETRAC', '',
             f"Выбрано на 20 последовательностях для настройки (ByteTrack): **{label(chosen)}**. "
             'Мотоциклы исключены из сравнения (в UA-DETRAC не размечены).', '',
             '## Настройка (development, ByteTrack), лучшие варианты', '',
             '| Правила | Precision | Recall | F1 | Ошибка счёта |', '|---|---:|---:|---:|---:|']
    for g in sorted(grid, key=lambda g: -g['development']['f1'])[:8] + [g for g in grid if g['rules'] == DEFAULT]:
        d = g['development']
        lines.append(f"| {label(g['rules'])} | {d['precision']:.3f} | {d['recall']:.3f} | {d['f1']:.3f} | {100*d['total_count_error']:+.1f}% |")
    lines += ['', '## Итог на 20 оценочных последовательностях (один раз)', '',
              '| Трекер | Правила | Precision | Recall | F1 | Ошибка счёта | Точность класса |', '|---|---|---:|---:|---:|---:|---:|']
    for tracker, result in evaluation.items():
        for name in ('default', 'chosen'):
            d = result[name]
            lines.append(f"| {tracker} | {'прежние' if name == 'default' else 'выбранные'} | {d['precision']:.3f} | {d['recall']:.3f} | {d['f1']:.3f} | "
                         f"{100*d['total_count_error']:+.1f}% | {100*d['class_accuracy']:.1f}% |")
    (ROOT/'reports/COUNTING_RULES.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
