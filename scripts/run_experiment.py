"""Train and evaluate one reproducible vehicle detection experiment."""
import argparse
import csv
import json
import platform
from pathlib import Path
from time import perf_counter
import torch
import ultralytics
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]

def run(args):
    if Path(args.name).name != args.name or not args.name:
        raise ValueError('Experiment name must be a simple directory name')
    resume = getattr(args,'resume',False)
    last = ROOT/f'runs/experiments/{args.name}/weights/last.pt'
    if (ROOT/f'reports/{args.name}.json').exists() or ((ROOT/f'runs/experiments/{args.name}').exists() and not resume):
        raise ValueError('A completed experiment with this name exists; use a new name')
    if resume and not last.is_file():
        raise ValueError('Nothing to resume: no last.pt for this experiment')
    data = (ROOT/args.data).resolve()
    weights = getattr(args,'weights',None)
    if args.scratch and weights:
        raise ValueError('Cannot combine scratch and initialization weights')
    if weights and not Path(weights).is_file():
        raise ValueError('Initialization weights must exist locally')
    start = perf_counter()
    if resume:
        # Continues the interrupted run with its own saved settings, from the epoch after last.pt.
        model = YOLO(str(last))
        model.train(resume=True)
    else:
        model = YOLO(weights or ('yolov8n.yaml' if args.scratch else 'yolov8n.pt'))
        model.train(data=str(data),epochs=args.epochs,imgsz=args.imgsz,batch=args.batch,
                    device=args.device,workers=0,seed=42,pretrained=not args.scratch,
                    project=str(ROOT/'runs/experiments'),name=args.name,exist_ok=False,
                    patience=10,cache=False,close_mosaic=min(5,args.epochs),plots=True,
                    optimizer=getattr(args,'optimizer','auto'),lr0=getattr(args,'lr0',.01))
    elapsed = perf_counter()-start
    best = Path(model.trainer.best)
    if resume:
        # The time column restarts with every resumed session, and interrupted runs also include
        # stalls (sleep, swapping), so no honest training time can be reported for them.
        elapsed = None
    detector = YOLO(str(best))
    # Validation threshold defaults to the library evaluation setting, independent of video confidence.
    validation = detector.val(data=str(data),split='val',imgsz=args.imgsz,batch=args.batch,
                              device=args.device,workers=0,project=str(ROOT/'runs/evaluation'),
                              name=f'{args.name}-val',plots=True)
    val_metrics = dict(validation.results_dict)
    val_classes = {detector.names[int(c)]:{'precision':float(validation.box.p[i]),'recall':float(validation.box.r[i]),
                                           'mAP50':float(validation.box.ap50[i]),'mAP50_95':float(validation.box.ap[i])}
                   for i,c in enumerate(validation.box.ap_class_index)}
    test = detector.val(data=str(data),split='test',imgsz=args.imgsz,batch=args.batch,
                        device=args.device,workers=0,project=str(ROOT/'runs/evaluation'),
                        name=f'{args.name}-test',plots=True)
    result = {'name':args.name,'initialization':('local-checkpoint' if weights else 'random' if args.scratch else 'COCO-pretrained'),'initial_weights':str(Path(weights).resolve()) if weights else None,'optimizer_requested':getattr(args,'optimizer','auto'),'lr0_requested':getattr(args,'lr0',.01),
              'data':str(data),'epochs_completed':len(list(csv.DictReader((best.parent.parent/'results.csv').open()))),'epochs_requested':args.epochs,'imgsz':args.imgsz,'batch':args.batch,
              'device':args.device,'seed':42,'training_seconds':elapsed,'best_weights':str(best),
              'validation':val_metrics,'validation_by_class':val_classes,'test':dict(test.results_dict),
              'test_by_class':{detector.names[int(c)]:{'precision':float(test.box.p[i]),'recall':float(test.box.r[i]),
                                                    'mAP50':float(test.box.ap50[i]),'mAP50_95':float(test.box.ap[i])}
                               for i,c in enumerate(test.box.ap_class_index)},
              'test_speed_ms':test.speed,'versions':{'python':platform.python_version(),'torch':torch.__version__,
                                                     'ultralytics':ultralytics.__version__},
              'resumed':resume,'training_time_note':'Not recorded: the run was interrupted and resumed.' if resume else None,'platform':platform.platform(), 'mps_determinism_note':'Some scatter/index operations are nondeterministic even with seed=42.', 'training_directory':str(best.parent.parent)}
    temporary = ROOT/f'reports/{args.name}.tmp'
    temporary.write_text(json.dumps(result,indent=2))
    temporary.replace(ROOT/f'reports/{args.name}.json')
    print(json.dumps(result,indent=2),flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--name',required=True)
    parser.add_argument('--data',default='configs/visdrone-pilot.yaml')
    parser.add_argument('--scratch',action='store_true')
    parser.add_argument('--weights',help='Local initialization checkpoint')
    parser.add_argument('--optimizer',default='auto')
    parser.add_argument('--lr0',type=float,default=.01)
    parser.add_argument('--epochs',type=int,default=15)
    parser.add_argument('--imgsz',type=int,default=416)
    parser.add_argument('--batch',type=int,default=8)
    parser.add_argument('--device',default='mps')
    parser.add_argument('--resume',action='store_true',help='Continue an interrupted experiment from its last.pt (give the same --name, --data and --weights)')
    run(parser.parse_args())
