import argparse
from pathlib import Path
from ultralytics import YOLO
ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--weights',required=True)
    parser.add_argument('--name',required=True)
    args=parser.parse_args()
    # Fixed first five validation images, not chosen according to model predictions.
    files=sorted((ROOT/'data/visdrone-vehicles/images/val').glob('*.jpg'))[:5]
    model=YOLO(str(ROOT/args.weights))
    model.predict(source=[str(p) for p in files],conf=.3,imgsz=416,device='cpu',save=True,
                  project=str(ROOT/'outputs/predictions'),name=args.name,verbose=False)
