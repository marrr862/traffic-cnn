"""One-to-one counting-event evaluation against explicit video references."""
import math
import re
from collections import Counter
import numpy as np
from lap import lapjv

def match_events(references,events,tolerance=6):
    """One-to-one interval assignment: prioritize matches, then class agreement."""
    if not isinstance(tolerance,int) or tolerance < 0:
        raise ValueError('Tolerance must be a nonnegative integer')
    nr, npred = len(references), len(events)
    size = nr + npred
    if size == 0:
        return {'tolerance_frames':tolerance,'matched_events':0,'matched_pairs':[],'unmatched_reference_events':[],'unmatched_predicted_events':[],'matched_class_disagreements':[]}
    normalization = max([1]+[r['frame_interval'][1] for r in references]+[int(e['frame']) for e in events])
    cost = np.zeros((size,size),dtype=np.float64)
    cost[:nr,:npred] = 100
    cost[:nr,npred:] = 1
    cost[nr:,:npred] = 1
    for i,ref in enumerate(references):
        low,high = ref['frame_interval']
        for j,event in enumerate(events):
            frame = int(event['frame'])
            if event['direction'] == ref['direction'] and low-tolerance <= frame <= high+tolerance:
                penalty = 0 if event['vehicle_class'] == ref['class'] else .5/size
                cost[i,j] = penalty + 0.01*abs(frame-(low+high)/2)/(size*normalization)
    _, assignment, _ = lapjv(cost)
    pairs = [(i,int(assignment[i])) for i in range(nr) if assignment[i] < npred and cost[i,assignment[i]] < 1]
    matched_refs = {i for i,j in pairs}
    matched_preds = {j for i,j in pairs}
    return {'tolerance_frames':tolerance,'matched_events':len(pairs),
            'matched_pairs':[{'reference':references[i],'predicted':events[j]} for i,j in pairs],
            'unmatched_reference_events':[references[i] for i in range(nr) if i not in matched_refs],
            'unmatched_predicted_events':[events[j] for j in range(npred) if j not in matched_preds],
            'matched_class_disagreements':[{'reference':references[i],'predicted':events[j]} for i,j in pairs if references[i]['class'] != events[j]['vehicle_class']],
            'note':'Approximate interval matching, not a validated benchmark. Equal total counts can hide missed and duplicated events.'}


def evaluate_run(summary, reference, events, tolerance=6):
    """Reject references for another video, line or time axis before matching."""
    checksum = reference.get('source_sha256','')
    if not re.fullmatch(r'[0-9a-f]{64}',checksum) or checksum != summary.get('source_sha256'):
        raise ValueError('Reference source_sha256 must match the analyzed video')
    if reference.get('line') != summary.get('line'):
        raise ValueError('Reference and analysis counting lines differ')
    fps = reference.get('fps')
    if not isinstance(fps,(int,float)) or not math.isfinite(fps) or not math.isclose(fps,summary['source_fps'],rel_tol=1e-6):
        raise ValueError('Reference and analysis FPS differ')
    references = reference.get('events')
    if not isinstance(references,list):
        raise ValueError('Reference events must be a list')
    directions = {'negative_to_positive','positive_to_negative'}
    classes = {'car','van','truck','bus','motorcycle'}
    for event in references:
        if not isinstance(event,dict):
            raise ValueError('Reference events must be objects')
        interval = event.get('frame_interval')
        if not isinstance(interval,list) or len(interval) != 2 or not all(type(n) is int for n in interval) or not 0 <= interval[0] <= interval[1] < summary['frames']:
            raise ValueError('Reference frame_interval must be within the video')
        if event.get('direction') not in directions or event.get('class') not in classes:
            raise ValueError('Invalid reference direction or vehicle class')
    if len(events) != summary['crossings']:
        raise ValueError('CSV event count differs from summary')
    for event in events:
        try:
            frame = int(event['frame'])
        except (ValueError,TypeError,KeyError) as exc:
            raise ValueError('Invalid prediction frame') from exc
        if str(frame) != str(event['frame']) or not 0 <= frame < summary['frames'] or event.get('direction') not in directions or event.get('vehicle_class') not in classes:
            raise ValueError('Invalid predicted event')
    temporal = match_events(references,events,tolerance)
    matched = temporal['matched_events']
    precision = matched/len(events) if events else None
    recall = matched/len(references) if references else None
    f1 = 2*matched/(len(events)+len(references)) if events or references else None
    by_direction = {d:dict(observed=sum(e['direction']==d for e in events),reference=sum(e['direction']==d for e in references)) for d in sorted(directions)}
    for values in by_direction.values():
        values['absolute_difference'] = abs(values['observed']-values['reference'])
    return dict(reference_type=reference.get('reference_type','Unspecified annotation provenance'),
                annotation_status=reference.get('annotation_status','unverified'),
                temporal_event_check=temporal, event_precision=precision,event_recall=recall,event_f1=f1,
                observed_total=len(events),reference_total=len(references),absolute_count_difference=abs(len(events)-len(references)),
                by_direction=by_direction,observed_by_class=dict(Counter(e['vehicle_class'] for e in events)),
                reference_by_class=dict(Counter(e['class'] for e in references)),
                limitations=reference.get('limitations','Reference annotation quality has not been established.'),
                source_sha256=checksum,line=summary['line'],processing_fps=summary['processing_fps'])
