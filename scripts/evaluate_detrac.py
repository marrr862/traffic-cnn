"""External vehicle detection and counting check using published UA-DETRAC XML."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from ultralytics import YOLO
from traffic_cnn.evaluation import match_events

ROOT = Path(__file__).resolve().parents[1]

def xml_frames(path, limit):
    root = ET.parse(path).getroot()
    ignored = [[float(b.get(k)) for k in ('left','top','width','height')] for b in root.findall('ignored_region/box')]
    frames = []
    for frame in root.findall('frame')[:limit]:
        targets = []
        for target in frame.findall('target_list/target'):
            box = target.find('box'); attr = target.find('attribute')
            x,y,w,h = [float(box.get(k)) for k in ('left','top','width','height')]
            targets.append(dict(id=int(target.get('id')),box=[x,y,x+w,y+h],kind=attr.get('vehicle_type')))
        frames.append((int(frame.get('num'))-1,targets))
    if [f for f,_ in frames] != list(range(limit)): raise ValueError('Non-contiguous annotation frames')
    return root,ignored,frames

def in_ignore(box, regions):
    x,y = (box[0]+box[2])/2,(box[1]+box[3])/2
    return any(a <= x <= a+w and b <= y <= b+h for a,b,w,h in regions)

def crossing_reference(frames, line_y=324):
    previous, counted, events = {},set(),[]
    for frame,targets in frames:
        for target in targets:
            identity,box = target['id'],target['box']
            x,y = (box[0]+box[2])/2,box[3]
            side = 1 if y > line_y+4 else -1 if y < line_y-4 else 0
            if not side: continue
            old = previous.get(identity)
            if old and old[2] != side and frame-old[0] <= 30 and identity not in counted:
                ratio = (line_y-old[1][1])/(y-old[1][1])
                cross_x = old[1][0]+ratio*(x-old[1][0])
                if 0 <= cross_x <= 959:
                    events.append(dict(label=f'published-track-{identity}',class_name=target['kind'],frame_interval=[old[0],frame],direction='negative_to_positive' if side==1 else 'positive_to_negative'))
                    counted.add(identity)
            previous[identity]=(frame,(x,y),side)
    # Keep the original taxonomy, including others; no truck relabeling.
    return [dict(label=e['label'],**{'class':e['class_name']},frame_interval=e['frame_interval'],direction=e['direction']) for e in events]

def iou(a,b):
    if not b: return np.empty(0)
    b=np.asarray(b); a=np.asarray(a)
    inter=np.maximum(0,np.minimum(a[2:],b[:,2:])-np.maximum(a[:2],b[:,:2])).prod(axis=1)
    area=(a[2]-a[0])*(a[3]-a[1]); areas=(b[:,2]-b[:,0])*(b[:,3]-b[:,1])
    return inter/(area+areas-inter+1e-9)

def detection_check(model, images, frames, ignored, imgsz, device):
    records=[]; total=0; excluded=0
    for index,((frame,targets),image) in enumerate(zip(frames,images)):
        truth=[t['box'] for t in targets if not in_ignore(t['box'],ignored)]
        total+=len(truth)
        result=model.predict(str(image),conf=.001,imgsz=imgsz,device=device,verbose=False)[0]
        predictions=[]
        for box,confidence,cls in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist(),result.boxes.cls.int().cpu().tolist()):
            if model.names[cls] not in ('car','van','truck','bus','motorcycle'): continue
            if in_ignore(box,ignored): excluded+=1; continue
            predictions.append((confidence,box))
        predictions.sort(reverse=True,key=lambda p:p[0])
        matches=np.zeros((len(predictions),10),dtype=bool)
        for j,threshold in enumerate(np.arange(.5,1,.05)):
            used=set()
            for k,(_,box) in enumerate(predictions):
                overlaps=iou(box,truth)
                candidates=[n for n in np.argsort(-overlaps) if n not in used and overlaps[n]>=threshold]
                if candidates: used.add(candidates[0]); matches[k,j]=True
        records.extend((score,matches[k].tolist()) for k,(score,_) in enumerate(predictions))
        if (index+1)%100==0: print(f'detection {imgsz}: {index+1}/{len(images)}',flush=True)
    records.sort(reverse=True,key=lambda p:p[0]); ap=[]
    scores=np.array([r[0] for r in records]); matched=np.array([r[1] for r in records],dtype=bool).reshape(-1,10)
    for j in range(10):
        tp=np.cumsum(matched[:,j]); fp=np.cumsum(~matched[:,j]); recall=tp/max(total,1); precision=tp/np.maximum(tp+fp,1)
        envelope=np.maximum.accumulate(precision[::-1])[::-1]
        ap.append(float(np.mean([envelope[recall>=r].max() if np.any(recall>=r) else 0 for r in np.linspace(0,1,101)])))
    selected=scores>=.3; tp=int(matched[selected,0].sum()); observed=int(selected.sum())
    return dict(vehicle_AP50=ap[0],vehicle_AP50_95=float(np.mean(ap)),annotated_boxes=total,predictions_above_0_3=observed,precision_at_0_3=tp/observed if observed else None,recall_at_0_3=tp/total if total else None,ignored_predictions=excluded,protocol='Class-agnostic vehicle; greedy IoU matching per image, 101-point precision envelope. Remove GT/predictions whose box centers lie inside published ignore rectangles. Custom protocol, not official UA-DETRAC or five-class VisDrone mAP.')

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--sequence',default='MVI_39031'); parser.add_argument('--frames',type=int,default=300); parser.add_argument('--device',default='mps'); parser.add_argument('--models',default='vehicle-finetune-full:640,vehicle-expanded-full:960',help='name:imgsz,...'); args=parser.parse_args()
    folder=ROOT/'data/ua-detrac'/args.sequence
    images=sorted(folder.glob('*.jpg'))[:args.frames]
    if len(images)!=args.frames: raise ValueError('Download the requested frames first')
    manifest=json.loads((folder/'manifest.json').read_text())
    if hashlib.sha256((folder/'annotations.xml').read_bytes()).hexdigest()!=manifest['xml_sha256']:
        raise ValueError('Annotation SHA256 differs from download manifest')
    for image in images:
        if hashlib.sha256(image.read_bytes()).hexdigest()!=manifest['images'].get(image.name):
            raise ValueError(f'Image SHA256 differs from download manifest: {image.name}')
    root,ignored,frames=xml_frames(folder/'annotations.xml',args.frames)
    video=ROOT/'data/video'/f'detrac-{args.sequence}-{args.frames}.mp4'
    if not video.exists():
        writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'avc1'),25,(960,540))
        if not writer.isOpened(): raise ValueError('Cannot encode reference video')
        for image in images:
            picture=cv2.imread(str(image))
            if picture is None or picture.shape[:2]!=(540,960): raise ValueError('Unexpected image dimensions')
            writer.write(picture)
        writer.release()
    references=crossing_reference(frames)
    reference=dict(sequence=args.sequence,frames=args.frames,fps=25,line=[0,324,959,324],source_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),events=references,annotation_status='published_dataset',reference_type='Published UA-DETRAC XML trajectories; automatically derived crossing events',limitations='First 12 seconds of one test camera only; line preselected at 60% height; bottom-center points, 4px hysteresis, max gap 30 frames, one event per published ID. Derived events are not a separately human-verified line-count annotation.',ignored_regions=ignored)
    refpath=ROOT/'reports'/f'detrac-reference-{args.sequence}.json'; refpath.write_text(json.dumps(reference,indent=2))
    results=[]
    for name,imgsz in [(m.split(':')[0],int(m.split(':')[1])) for m in args.models.split(',')]:
        weights=ROOT/'runs/experiments'/name/'weights/best.pt'
        output=ROOT/'outputs'/f'demo-full-detrac-{name}-{imgsz}'
        if not (output/'summary.json').exists():
            subprocess.run([sys.executable,'-m','traffic_cnn.cli','analyze','--video',str(video),'--weights',str(weights),'--output',str(output),'--imgsz',str(imgsz),'--device',args.device,'--line','0','324','959','324','--interval-seconds','5'],cwd=ROOT,check=True)
        summary=json.loads((output/'summary.json').read_text())
        if summary['source_sha256']!=reference['source_sha256'] or summary['frames']!=args.frames or summary['imgsz']!=imgsz or Path(summary['weights']).resolve()!=weights.resolve() or summary['line']!=reference['line']:
            raise ValueError('Existing analysis does not match requested input/parameters; choose a fresh result directory')
        with (output/'crossings.csv').open() as handle: predicted=list(csv.DictReader(handle))
        if len(predicted)!=summary['crossings']: raise ValueError('Crossing CSV differs from summary')
        temporal=match_events(references,predicted,tolerance=6); n=temporal['matched_events']; denominator=len(references)+len(predicted)
        counting=dict(reference_total=len(references),predicted_total=len(predicted),matched_events=n,missed_events=len(references)-n,extra_events=len(predicted)-n,event_precision=n/len(predicted) if predicted else None,event_recall=n/len(references) if references else None,event_f1=2*n/denominator if denominator else None,matched_pairs=temporal['matched_pairs'],class_metrics='Not evaluated: published others does not equal truck, taxonomy differs',processing_fps=json.loads((output/'summary.json').read_text())['processing_fps'])
        detection=detection_check(YOLO(str(weights)),images,frames,ignored,imgsz,args.device)
        results.append(dict(name=name,imgsz=imgsz,counting=counting,detection=detection))
        report=dict(reference=reference,results=results,training_on_detrac=False,limitations='External transfer check, one camera prefix; correlated frames. Models were selected on VisDrone validation before this check. Comparison changes both checkpoint and resolution and cannot isolate training-data effects. No official ranking claim. Detection ignores published regions; counting includes all published trajectories and may penalize detections from unannotated regions.')
        (ROOT/'reports'/f'detrac-comparison-{args.sequence}.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(results,indent=2),flush=True)

if __name__=='__main__': main()
