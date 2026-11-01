"""Compare inference sizes on fixed splits; select size using validation only."""
import argparse
import hashlib
import json
from pathlib import Path
from ultralytics import YOLO

ROOT=Path(__file__).resolve().parents[1]


def evaluate(detector,data,split,imgsz,device,name):
    value=detector.val(data=data,split=split,imgsz=imgsz,batch=8,device=device,workers=0,project=str(ROOT/'runs/evaluation'),name=name,plots=True)
    return dict(metrics=dict(value.results_dict),by_class={detector.names[int(c)]:dict(precision=float(value.box.p[i]),recall=float(value.box.r[i]),mAP50=float(value.box.ap50[i]),mAP50_95=float(value.box.ap[i])) for i,c in enumerate(value.box.ap_class_index)},speed_ms=value.speed)


def main(args):
    if Path(args.name).name != args.name or args.imgsz<=0:
        raise ValueError('Use a simple experiment name and positive image size')
    path=ROOT/'reports'/f'{args.name}.json'
    report=json.loads(path.read_text());weights=Path(report['best_weights'])
    destination=ROOT/'reports/resolution-comparison.json'
    if destination.exists():raise ValueError('Resolution comparison already exists; preserve it before starting a new comparison')
    detector=YOLO(str(weights))
    baseline=report['imgsz']
    comparison=dict(name=args.name,weights_sha256=hashlib.sha256(weights.read_bytes()).hexdigest(),protocol='Same trained checkpoint and original fixed val/test. Size selected by validation only; test is descriptive and has previously been used. Speed values are library measurements in this execution, not a controlled video throughput benchmark.',sizes={str(baseline):dict(validation=dict(metrics=report['validation'],by_class=report['validation_by_class']),test=dict(metrics=report['test'],by_class=report['test_by_class']))})
    trial=dict(validation=evaluate(detector,report['data'],'val',args.imgsz,args.device,f'{args.name}-resolution-{args.imgsz}-val'))
    chosen=args.imgsz if trial['validation']['metrics']['metrics/mAP50-95(B)']>report['validation']['metrics/mAP50-95(B)'] else baseline
    trial['test']=evaluate(detector,report['data'],'test',args.imgsz,args.device,f'{args.name}-resolution-{args.imgsz}-test')
    comparison['sizes'][str(args.imgsz)]=trial;comparison['selected_imgsz_by_validation']=chosen
    destination.write_text(json.dumps(comparison,indent=2))
    report['recommended_inference_imgsz']=chosen
    path.write_text(json.dumps(report,indent=2))
    recommendation=ROOT/'reports/recommended-model.json'
    if recommendation.exists():
        value=json.loads(recommendation.read_text())
        if value['name']==args.name:value['inference_imgsz']=chosen;recommendation.write_text(json.dumps(value,indent=2))
    print(json.dumps(comparison,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--name',required=True);parser.add_argument('--imgsz',type=int,default=960);parser.add_argument('--device',default='mps');main(parser.parse_args())
