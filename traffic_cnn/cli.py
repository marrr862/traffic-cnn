import argparse
import csv
import json
import math
import hashlib
import signal
from collections import Counter, deque
from pathlib import Path
from time import perf_counter
from .counting import LineCounter, DuplicateGuard
from .tracklets import Tracklets
from .flow import flow_windows
from .geometry import validate_line, direction_labels
from .calibration import Calibration, SpeedEstimator, speed_statistics
from .traffic_state import density as zone_density, level_of_service, fundamental_check, plausibility_issues
from .heatmap import Heatmap, draw_trajectories
from .motion import MotionMeter
from .sources import is_live, resolve, describe, LatestFrameReader


def analyze(args):
    import cv2
    import numpy as np
    from ultralytics import YOLO
    live = is_live(args.video)
    if not Path(args.weights).is_file():
        raise ValueError('Trained weights must exist locally')
    if not live and not Path(args.video).is_file():
        raise ValueError('Video file must exist (or give a webcam index / stream URL)')
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    if any((out/name).exists() for name in ('annotated.mp4','crossings.csv','tracks.csv','summary.json','frame_stats.csv','tracks_summary.csv','flow_windows.csv')):
        raise ValueError('Choose a new output directory: results already exist')
    if getattr(args,'calibration',None) and not Path(args.calibration).is_file():
        raise ValueError('Calibration file must exist')
    model = YOLO(args.weights)
    digest = hashlib.sha256()
    if live:
        digest.update(str(args.video).encode())  # a stream has no fixed content to hash
    else:
        with Path(args.video).open('rb') as source_handle:
            for chunk in iter(lambda:source_handle.read(1024*1024),b''):
                digest.update(chunk)
    stop = {'requested': False}
    def request_stop(*_):
        stop['requested'] = True
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    tracker_config = out/'tracker.yaml'
    baseline = args.baseline_tracking
    # ByteTrack two-stage association: detections down to low_threshold reach the tracker
    # (second association of existing tracks); new tracks and the first association use args.conf.
    low_threshold = min(0.1,args.conf/2)
    high = args.conf
    low = low_threshold
    tracker_config.write_text(f'tracker_type: bytetrack\ntrack_high_thresh: {high}\ntrack_low_thresh: {low}\nnew_track_thresh: {high}\ntrack_buffer: 30\nmatch_thresh: 0.8\nfuse_score: true\n')
    ids = [i for i, name in model.names.items() if name in args.classes.split(',')]
    tiled = None
    if getattr(args,'tile',0):
        from .tiling import TiledTracker  # small vehicles (drone / high-resolution frames)
        tiled = TiledTracker(model,tracker_config,tile=args.tile,overlap=args.tile_overlap,imgsz=args.imgsz,full_frame=True)
    if not ids:
        raise ValueError(f'No requested classes in model: {model.names}')
    cap = cv2.VideoCapture(resolve(args.video))
    writer = None
    track_handle = None
    reader = None
    try:
        if not cap.isOpened():
            raise ValueError('Cannot open video source')
        fps = cap.get(cv2.CAP_PROP_FPS)
        w, h = int(cap.get(3)), int(cap.get(4))
        if live:
            reader = LatestFrameReader(cap)
            ok, probe, _, _ = reader.read(0, timeout=20)
            if not ok:
                raise ValueError('No frames received from the live source')
            h, w = probe.shape[:2]
            fps = float(getattr(args, 'live_fps', 10))  # nominal rate of the written video; real times are measured
        if not math.isfinite(fps) or fps <= 0 or min(w,h) <= 0:
            raise ValueError('Invalid video FPS or dimensions')
        # An accelerated (time-lapse) video covers time_scale real seconds per video second:
        # times, speeds and flows use the real-time frame rate, the written video keeps fps.
        time_scale = float(getattr(args,'time_scale',1.0) or 1.0)
        if not math.isfinite(time_scale) or time_scale <= 0:
            raise ValueError('Time scale must be finite and positive')
        if live and time_scale != 1:
            raise ValueError('Time scale applies to recorded videos only')
        time_fps = fps/time_scale
        motion = MotionMeter()
        line = validate_line(args.line or [0,h*0.6,w-1,h*0.6],w,h)
        counter = LineCounter(tuple(line[:2]),tuple(line[2:]))
        extra_lines = [validate_line(l,w,h) for l in (getattr(args,'extra_line',None) or [])]
        extra_counters = [LineCounter(tuple(l[:2]),tuple(l[2:])) for l in extra_lines]
        guard_enabled = getattr(args,'duplicate_guard',True)
        start_counting = getattr(args,'start_crossings',True)
        guards = [DuplicateGuard() for _ in range(1+len(extra_lines))]
        duplicates = []
        line_events = []
        calibration = Calibration.load(args.calibration) if getattr(args,'calibration',None) else None
        speed = SpeedEstimator(calibration,time_fps) if calibration else None
        heat = Heatmap(w,h)
        full_paths, first_frame_image = {}, None
        tracklets = Tracklets()
        video_codec = 'avc1'
        writer = cv2.VideoWriter(str(out/'annotated.mp4'),cv2.VideoWriter_fourcc(*video_codec),fps,(w,h))
        if not writer.isOpened():
            writer.release()
            video_codec = 'mp4v'
            writer = cv2.VideoWriter(str(out/'annotated.mp4'),cv2.VideoWriter_fourcc(*video_codec),fps,(w,h))
        if not writer.isOpened():
            raise ValueError('Cannot create output video')
        track_handle = (out/'tracks.csv').open('w',newline='')
        track_table = csv.DictWriter(track_handle,fieldnames=['frame','time_seconds','track_id','raw_track_id','vehicle_class','confidence','x','y','box_width','box_height','world_x_m','world_y_m','speed_kmh'])
        track_table.writeheader()
        paths, last_seen, observed_ids = {}, {}, set()
        movements, frame_stats = {}, []
        events, counts, n = [], Counter(), 0
        zone_crossings = 0
        start = perf_counter()
        last_preview = 0.0
        t_now = 0.0
        sequence = 0
        max_seconds = getattr(args, 'max_seconds', None)
        while not stop['requested']:
            if live:
                ok, frame, stamp, sequence = reader.read(sequence)
                if not ok:
                    break
                t_now = stamp - start
                if max_seconds and t_now >= max_seconds:
                    break
            else:
                ok, frame = cap.read()
                if not ok:
                    break
                t_now = n/time_fps
                if max_seconds and t_now >= max_seconds:
                    break
            if first_frame_image is None:
                first_frame_image = frame.copy()
            if tiled is not None:
                result = tiled.track(frame,classes=ids,conf=low_threshold,iou=getattr(args,'nms_iou',0.5),
                                     agnostic=getattr(args,'agnostic_nms',True) or not baseline,device=args.device)
            else:
                result = model.track(frame,persist=True,tracker=str(tracker_config),classes=ids,
                                     conf=low_threshold,agnostic_nms=getattr(args,'agnostic_nms',True) or not baseline,iou=getattr(args,'nms_iou',0.5),device=args.device,imgsz=args.imgsz,verbose=False)[0]
            boxes = result.boxes
            visible, in_zone, labels = 0, 0, []
            if boxes is not None and boxes.id is not None:
                detections = [(raw,box,cls,confidence) for box,raw,cls,confidence in zip(boxes.xyxy.cpu().tolist(),boxes.id.int().cpu().tolist(),boxes.cls.int().cpu().tolist(),boxes.conf.cpu().tolist())]
                observations = [(raw,raw,box,cls,confidence) for raw,box,cls,confidence in detections] if baseline else tracklets.update(detections,n)
                frame_boxes = {identity:box for identity,_,box,_,_ in observations}
                for identity, raw, box, cls, confidence in observations:
                    visible += 1
                    point = ((box[0]+box[2])/2,box[3])
                    movement = movements.setdefault(identity,dict(first_frame=n,last_frame=n,first_point=point,last_point=point,distance_pixels=0,vehicle_class=model.names[cls],observations=0))
                    if n-movement['last_frame'] <= tracklets.max_gap:
                        movement['distance_pixels'] += math.dist(point,movement['last_point'])
                    movement.update(last_frame=n,last_point=point,vehicle_class=model.names[cls],observations=movement['observations']+1)
                    paths.setdefault(identity,deque(maxlen=30)).append(point)
                    last_seen[identity] = n
                    observed_ids.add(identity)
                    heat.add(point)
                    motion.update(identity,point,box[3]-box[1],n)
                    if n % 2 == 0:
                        trail = full_paths.setdefault(identity,[model.names[cls],[]])[1]
                        if len(trail) >= 600:
                            del trail[::2]  # keep the trajectory shape with bounded memory
                        trail.append(point)
                        full_paths[identity][0] = model.names[cls]
                    kmh, world = None, (None,None)
                    if calibration is not None:
                        kmh = speed.update(identity,point,n,t=t_now)
                        if calibration.contains(point):
                            in_zone += 1
                            world = tuple(calibration.to_world(point)[0])
                    if kmh is not None:
                        labels.append((box,f'{kmh:.0f} km/h'))
                    track_table.writerow(dict(frame=n,time_seconds=round(t_now,4),track_id=identity,raw_track_id=raw,vehicle_class=model.names[cls],confidence=confidence,x=point[0],y=point[1],box_width=round(box[2]-box[0],1),box_height=round(box[3]-box[1],1),
                                              world_x_m='' if world[0] is None else round(world[0],3),world_y_m='' if world[1] is None else round(world[1],3),speed_kmh='' if kmh is None else round(kmh,2)))
                    direction = counter.update(identity,point,n,size=box[3]-box[1] if start_counting else None)
                    if direction and guard_enabled:
                        original = guards[0].duplicate_of(identity,box,direction,n,frame_boxes)
                        if original is not None:
                            duplicates.append(dict(line_id=0,frame=n,time_seconds=round(t_now,4),track_id=identity,duplicate_of=original,vehicle_class=model.names[cls],direction=direction))
                            direction = None
                    if direction:
                        counts[direction] += 1
                        if calibration is not None and calibration.contains(point):
                            zone_crossings += 1
                        events.append(dict(frame=n,time_seconds=round(t_now,4),track_id=identity,
                                           vehicle_class=model.names[cls],direction=direction,speed_kmh='' if kmh is None else round(kmh,2)))
                        events[-1]['line_id'] = 0
                        line_events.append(events[-1])
                    for index,extra in enumerate(extra_counters,start=1):
                        extra_direction = extra.update(identity,point,n,size=box[3]-box[1] if start_counting else None)
                        if extra_direction and guard_enabled:
                            original = guards[index].duplicate_of(identity,box,extra_direction,n,frame_boxes)
                            if original is not None:
                                duplicates.append(dict(line_id=index,frame=n,time_seconds=round(t_now,4),track_id=identity,duplicate_of=original,vehicle_class=model.names[cls],direction=extra_direction))
                                extra_direction = None
                        if extra_direction:
                            line_events.append(dict(line_id=index,frame=n,time_seconds=round(t_now,4),track_id=identity,vehicle_class=model.names[cls],direction=extra_direction,speed_kmh='' if kmh is None else round(kmh,2)))
            stat = dict(frame=n,time_seconds=round(t_now,4),visible_tracked_vehicles=visible,cumulative_crossings=len(events))
            if calibration is not None:
                k, k_lane = zone_density(in_zone,calibration.length_m,calibration.lanes)
                stat.update(vehicles_in_zone=in_zone,density_per_km=k,density_per_km_per_lane='' if k_lane is None else k_lane)
            frame_stats.append(stat)
            for identity in list(paths):
                if n-last_seen[identity] > 30:
                    del paths[identity], last_seen[identity]
            if n % 100 == 0:
                for line_counter in [counter,*extra_counters,*guards]:
                    line_counter.forget(n)
                if speed is not None:
                    speed.forget(t_now)
                motion.forget(n)
            display = result.plot()
            for trail in paths.values():
                if len(trail) > 1:
                    cv2.polylines(display,[np.array(trail,dtype=np.int32)],False,(0,150,255),2)
            scale = max(1.0,w/1280)
            if calibration is not None:
                cv2.polylines(display,[np.array(calibration.image_points,dtype=np.int32)],True,(255,255,0),max(1,int(2*scale)))
            for box,text in labels:
                origin = (int(box[0]),min(h-5,int(box[3]+28*scale)))
                cv2.putText(display,text,origin,cv2.FONT_HERSHEY_SIMPLEX,0.8*scale,(0,0,0),int(5*scale))
                cv2.putText(display,text,origin,cv2.FONT_HERSHEY_SIMPLEX,0.8*scale,(255,255,255),int(2*scale))
            cv2.line(display,tuple(map(int,line[:2])),tuple(map(int,line[2:])),(0,255,255),max(2,int(2*scale)))
            for index,extra in enumerate(extra_lines,start=1):
                cv2.line(display,tuple(map(int,extra[:2])),tuple(map(int,extra[2:])),(255,0,255),max(2,int(2*scale)))
            hud = f'Crossings: {len(events)}'
            if calibration is not None:
                hud += f' | In zone: {in_zone}'
            cv2.putText(display,hud,(15,int(40*scale)),cv2.FONT_HERSHEY_SIMPLEX,1.0*scale,(0,0,0),int(6*scale))
            cv2.putText(display,hud,(15,int(40*scale)),cv2.FONT_HERSHEY_SIMPLEX,1.0*scale,(0,255,255),int(2*scale))
            writer.write(display)
            n += 1
            if perf_counter()-last_preview >= 0.5:
                # Live preview for the interface (small JPEG, replaced atomically)
                last_preview = perf_counter()
                small = cv2.resize(display,(960,round(h*960/w))) if w > 960 else display
                cv2.imwrite(str(out/'preview.tmp.jpg'),small,[cv2.IMWRITE_JPEG_QUALITY,80])
                (out/'preview.tmp.jpg').replace(out/'preview.jpg')
            if n % 25 == 0 or live:
                if n % 5 == 0 or not live:
                    total = 0 if live else int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    progress = dict(frames=n,total_frames=total,crossings=len(events),seconds=round(t_now,1),max_seconds=max_seconds,live=live)
                    temporary = out/'progress.tmp'
                    temporary.write_text(json.dumps(progress))
                    temporary.replace(out/'progress.json')
        elapsed = perf_counter()-start
        if not n:
            raise ValueError('No decodable frames')
        if live:
            # Frames of a live source are taken as they arrive; use the measured rate for durations.
            fps = time_fps = n/max(t_now,1e-6)
        if speed is not None:
            # A vehicle that enters close to the line has no speed yet at the crossing
            # moment; use the median speed of the whole track measured afterwards.
            for event in line_events:
                if event['speed_kmh'] == '' and speed.track_speed(event['track_id']) is not None:
                    event['speed_kmh'] = round(speed.track_speed(event['track_id']),2)
        with (out/'crossings.csv').open('w',newline='') as f:
            table = csv.DictWriter(f,fieldnames=['frame','time_seconds','track_id','vehicle_class','direction','speed_kmh'],extrasaction='ignore')
            table.writeheader()
            table.writerows(events)
        with (out/'frame_stats.csv').open('w',newline='') as f:
            table = csv.DictWriter(f,fieldnames=list(frame_stats[0]))
            table.writeheader()
            table.writerows(frame_stats)
        interval = getattr(args, 'interval_seconds', 10)
        windows = flow_windows(events, frame_stats, time_fps, interval)
        with (out/'flow_windows.csv').open('w',newline='') as f:
            table = csv.DictWriter(f,fieldnames=list(windows[0]))
            table.writeheader()
            table.writerows(windows)
        with (out/'tracks_summary.csv').open('w',newline='') as f:
            fields = ['track_id','vehicle_class','first_frame','last_frame','observations','observed_duration_seconds','distance_pixels','mean_path_pixels_per_second','displacement_x_pixels','displacement_y_pixels','median_speed_kmh']
            table = csv.DictWriter(f,fieldnames=fields)
            table.writeheader()
            for identity,m in movements.items():
                duration = (m['last_frame']-m['first_frame'])/time_fps
                table.writerow(dict(track_id=identity,vehicle_class=m['vehicle_class'],first_frame=m['first_frame'],last_frame=m['last_frame'],observations=m['observations'],observed_duration_seconds=duration,distance_pixels=m['distance_pixels'],mean_path_pixels_per_second=m['distance_pixels']/duration if duration else 0,displacement_x_pixels=m['last_point'][0]-m['first_point'][0],displacement_y_pixels=m['last_point'][1]-m['first_point'][1],median_speed_kmh='' if speed is None or speed.track_speed(identity) is None else round(speed.track_speed(identity),2)))
        with (out/'duplicate_crossings.csv').open('w',newline='') as f:
            table = csv.DictWriter(f,fieldnames=['line_id','frame','time_seconds','track_id','duplicate_of','vehicle_class','direction'])
            table.writeheader()
            table.writerows(duplicates)
        with (out/'line_crossings.csv').open('w',newline='') as f:
            table = csv.DictWriter(f,fieldnames=['line_id','frame','time_seconds','track_id','vehicle_class','direction','speed_kmh'])
            table.writeheader()
            table.writerows(line_events)
        if first_frame_image is not None:
            cv2.imwrite(str(out/'heatmap.png'),heat.render(first_frame_image))
            cv2.imwrite(str(out/'trajectories.png'),draw_trajectories(first_frame_image,{k:(v[0],v[1]) for k,v in full_paths.items()}))
        summary = dict(tracked_ids=len(observed_ids),frames=n,duration_seconds=n/time_fps,crossings=len(events),by_direction=dict(counts),
                       source_video=str(args.video) if live else str(Path(args.video).resolve()),source_sha256=digest.hexdigest(),
                       mean_visible_tracked_vehicles=sum(s['visible_tracked_vehicles'] for s in frame_stats)/n,peak_visible_tracked_vehicles=max(s['visible_tracked_vehicles'] for s in frame_stats),
                       by_class=dict(Counter(e['vehicle_class'] for e in events)),
                       flow_vehicles_per_hour=len(events)*3600/(n/time_fps),processing_fps=n/elapsed,
                       line=line,direction_labels=direction_labels(line),weights=str(Path(args.weights).resolve()),confidence=args.conf,imgsz=args.imgsz,tiling=(dict(tile=args.tile,overlap=args.tile_overlap,full_frame=True) if getattr(args,'tile',0) else None),source_fps=fps,time_scale=time_scale,time_fps=time_fps,motion=motion.summary(fps,time_fps),video_codec=video_codec,interval_seconds=interval,
                       tracking=dict(mode='baseline' if baseline else 'continuity',detector_threshold=low_threshold,initialization_threshold=high,agnostic_nms=getattr(args,'agnostic_nms',True) or not baseline,nms_iou=getattr(args,'nms_iou',0.5),continuity_max_gap=0 if baseline else tracklets.max_gap,continuity_iou=tracklets.overlap,class_vote='instantaneous' if baseline else 'confidence-weighted history'),
                       source_description=describe(args.video),live_source=live,stopped_early=stop['requested'],
                       start_crossings=start_counting,
                       duplicate_guard=dict(enabled=guard_enabled,overlap=guards[0].overlap,window_frames=guards[0].window,
                                            suppressed=sum(d['line_id']==0 for d in duplicates),suppressed_all_lines=len(duplicates)),
                       limitations='One crossing per track ID; a second ID whose box coincides with an already counted vehicle is not counted. ID switches can duplicate counts; occlusion can cause misses. Flow extrapolates observed duration.'+('' if calibration else ' Speed is not calibrated.'))
        all_lines = [line]+extra_lines
        summary['lines'] = [dict(line_id=i,coordinates=l,crossings=sum(e['line_id']==i for e in line_events),
                                 by_direction=dict(Counter(e['direction'] for e in line_events if e['line_id']==i)),
                                 flow_vehicles_per_hour=sum(e['line_id']==i for e in line_events)*3600/(n/time_fps)) for i,l in enumerate(all_lines)]
        if calibration is not None:
            crossing_speeds = [float(e['speed_kmh']) for e in events if e['speed_kmh'] != '']
            track_speeds = [speed.track_speed(i) for i in movements]
            densities = [s['density_per_km'] for s in frame_stats]
            mean_k = sum(densities)/len(densities)
            mean_k_lane = mean_k/calibration.lanes if calibration.lanes else None
            spot = speed_statistics(crossing_speeds)
            summary['calibration'] = calibration.to_dict()
            summary['speed'] = dict(at_counting_line=spot,all_tracks=speed_statistics(track_speeds),
                                    method='Road-plane displacement over a 0.5–1.0 s window, median of recent estimates; flat road assumed.')
            summary['density'] = dict(mean_vehicles_in_zone=sum(s['vehicles_in_zone'] for s in frame_stats)/n,
                                      peak_vehicles_in_zone=max(s['vehicles_in_zone'] for s in frame_stats),
                                      mean_density_per_km=mean_k,mean_density_per_km_per_lane=mean_k_lane,
                                      level_of_service=level_of_service(mean_k_lane),zone_length_m=calibration.length_m,lanes=calibration.lanes)
            typical = summary['speed']['all_tracks']['median_kmh']
            summary['speed']['implausible_measurement_share'] = speed.rejected_share()
            summary['speed']['raw_median_kmh'] = speed.raw_median()
            summary['speed']['crossings_with_speed_share'] = len(crossing_speeds)/len(events) if events else None
            # q = k·v holds for one road section: flow is taken from crossings inside the calibrated zone,
            # where density is measured, not from parts of the line outside it.
            summary['line_share_in_zone'] = calibration.segment_share(line)
            if summary['line_share_in_zone'] > 0:
                zone_flow = zone_crossings*3600/(n/time_fps)
                summary['zone_flow'] = dict(crossings=zone_crossings,flow_vehicles_per_hour=zone_flow,
                                            flow_per_lane_per_hour=zone_flow/calibration.lanes if calibration.lanes else None)
                summary['fundamental_relation'] = fundamental_check(zone_flow,mean_k,spot['space_mean_kmh'])
            else:
                # The line does not cross the calibrated zone: its flow belongs to another road section.
                summary['zone_flow'] = summary['fundamental_relation'] = None
            issues = plausibility_issues(typical,speed.rejected,speed.rejected_share(),(summary['zone_flow'] or {}).get('flow_per_lane_per_hour'),summary['fundamental_relation'])
            summary['plausibility_issues'] = issues
            if issues:
                summary['plausibility_warning'] = ('Implausible measurements ('+', '.join(issues)+'): the video is probably accelerated (time-lapse), '
                                                   'the tracker duplicates vehicles or the calibration (size, lane count) is wrong. Speed and flow are not physically valid.')
            summary['limitations'] += ' Speed and density rely on the supplied road calibration (flat road, static camera); calibration error scales the speeds proportionally.'
        (out/'summary.json').write_text(json.dumps(summary,indent=2))
        final_progress = out/'progress.tmp'
        final_progress.write_text(json.dumps(dict(frames=n,total_frames=n,crossings=len(events),status='complete')))
        final_progress.replace(out/'progress.json')
        print(json.dumps(summary,indent=2))
    finally:
        if reader is not None:
            reader.stop()
        cap.release()
        if writer is not None:
            writer.release()
        if track_handle is not None:
            track_handle.close()


def main():
    parser = argparse.ArgumentParser(description='CNN training and traffic analysis')
    sub = parser.add_subparsers(dest='command',required=True)
    train = sub.add_parser('train')
    train.add_argument('--data',required=True)
    train.add_argument('--epochs',type=int,default=50)
    train.add_argument('--batch',type=int,default=4)
    train.add_argument('--imgsz',type=int,default=640)
    train.add_argument('--device',default='cpu')
    train.add_argument('--from-scratch',action='store_true')
    train.add_argument('--name',default='vehicles')
    val = sub.add_parser('evaluate')
    val.add_argument('--data',required=True)
    val.add_argument('--weights',required=True)
    val.add_argument('--split',choices=['val','test'],default='test')
    val.add_argument('--device',default='cpu')
    video = sub.add_parser('analyze')
    video.add_argument('--video',required=True)
    video.add_argument('--weights',required=True)
    video.add_argument('--output',default='outputs/video')
    video.add_argument('--line',nargs=4,type=float)
    video.add_argument('--classes',default='car,van,truck,bus,motorcycle')
    video.add_argument('--conf',type=float,default=0.3)
    video.add_argument('--device',default='cpu')
    video.add_argument('--imgsz',type=int,default=640)
    video.add_argument('--interval-seconds',type=float,default=10,help='Window length for flow_windows.csv in real seconds (video seconds times --time-scale)')
    video.add_argument('--extra-line',nargs=4,type=float,action='append',help='Additional counting segment x1 y1 x2 y2; repeatable')
    video.add_argument('--max-seconds',type=float,help='Stop after this many seconds (recommended for live sources)')
    video.add_argument('--time-scale',type=float,default=1.0,help='Real seconds per video second for accelerated (time-lapse) recordings, e.g. 4 for a 4x video; scales times, speeds and flows')
    video.add_argument('--live-fps',type=float,default=10,help='Nominal frame rate of the saved video for live sources')
    video.add_argument('--class-nms',action='store_false',dest='agnostic_nms',help='Class-wise NMS (default: class-agnostic, suppresses duplicate boxes of different classes)')
    video.add_argument('--nms-iou',type=float,default=0.5,help='NMS IoU threshold')
    video.add_argument('--tile',type=int,default=0,help='Tiled detection: tile size in pixels (e.g. 640) for small vehicles in drone or 4K frames; 0 = off')
    video.add_argument('--tile-overlap',type=float,default=0.2,help='Overlap between neighbouring tiles (0-0.5)')
    video.add_argument('--calibration',help='JSON road calibration: four image points and road rectangle size in metres')
    tracking = video.add_mutually_exclusive_group()
    tracking.add_argument('--baseline-tracking',action='store_true',dest='baseline_tracking',help='Standard ByteTrack settings (default)')
    tracking.add_argument('--continuity-tracking',action='store_false',dest='baseline_tracking',help='Experimental continuity and class voting; may worsen counting')
    video.set_defaults(baseline_tracking=True)
    video.add_argument('--no-start-crossings',action='store_false',dest='start_crossings',help='Do not count tracks first seen just past the line (vehicles that crossed before being detected)')
    video.add_argument('--no-duplicate-guard',action='store_false',dest='duplicate_guard',help='Count every track ID that crosses, even when its box coincides with an already counted vehicle')
    args = parser.parse_args()
    try:
        if args.command == 'analyze':
            if args.imgsz <= 0:
                raise ValueError('Image size must be positive')
            if not 0 < args.conf < 1:
                raise ValueError('Confidence must be between 0 and 1')
            if not math.isfinite(args.interval_seconds) or args.interval_seconds <= 0:
                raise ValueError('Interval must be finite and positive')
            analyze(args)
        else:
            from ultralytics import YOLO
            if args.command == 'train':
                if min(args.epochs,args.batch,args.imgsz) <= 0:
                    raise ValueError('Training parameters must be positive')
                model = YOLO('yolov8n.yaml' if args.from_scratch else 'yolov8n.pt')
                model.train(data=args.data,epochs=args.epochs,batch=args.batch,imgsz=args.imgsz,
                            device=args.device,workers=0,seed=42,project=str(Path('runs/train').resolve()),name=args.name,
                            pretrained=not args.from_scratch)
            else:
                metrics = YOLO(args.weights).val(data=args.data,split=args.split,device=args.device,workers=0)
                print(json.dumps(metrics.results_dict,indent=2))
    except (ValueError,FileNotFoundError) as exc:
        parser.error(str(exc))

if __name__ == '__main__':
    main()
