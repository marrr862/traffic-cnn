"""Check a local YOLO corpus before mixing or expanding data."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import yaml
from PIL import Image

EXTENSIONS={'.jpg','.jpeg','.png','.bmp','.webp','.tif','.tiff'}


def audit(config_path):
    config_path=Path(config_path).resolve()
    data=yaml.safe_load(config_path.read_text())
    root=Path(data['path'])
    if not root.is_absolute():root=(config_path.parent/root).resolve()
    names=data['names']
    names={i:name for i,name in enumerate(names)} if isinstance(names,list) else {int(i):name for i,name in names.items()}
    seen={};report=dict(config=str(config_path),names=names,splits={},limitations='SHA256 excludes exact cross-split duplicates only; camera identity and near-duplicate independence are not established.')
    for split in ['train','val','test']:
        entry=Path(data[split]);entry=entry if entry.is_absolute() else root/entry
        if entry.is_dir():paths=sorted(p for p in entry.rglob('*') if p.suffix.lower() in EXTENSIONS)
        elif entry.is_file() and entry.suffix=='.txt':
            paths=[Path(row) if Path(row).is_absolute() else entry.parent/row for row in entry.read_text().splitlines() if row.strip()]
        else:raise ValueError(f'Missing split: {entry}')
        if not paths:raise ValueError(f'Empty {split} split')
        counts=Counter();negatives=0;unique=set()
        for path in paths:
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            if digest in seen and seen[digest]!=split:raise ValueError(f'Cross-split duplicate: {path} is also in {seen[digest]}')
            seen[digest]=split;unique.add(digest)
            with Image.open(path) as image:image.verify()
            parts=list(path.parts)
            if 'images' not in parts:raise ValueError(f'Expected images/ directory: {path}')
            parts[parts.index('images')]='labels'
            label=Path(*parts).with_suffix('.txt')
            if not label.is_file():raise ValueError(f'Missing label (empty file required for negatives): {label}')
            rows=label.read_text().splitlines();negatives+=not rows
            for row in rows:
                tokens=row.split()
                if len(tokens)!=5:raise ValueError(f'Invalid detection row in {label}: {row}')
                category=int(tokens[0]);x,y,w,h=map(float,tokens[1:])
                if category not in names or not all(math.isfinite(v) for v in [x,y,w,h]) or w<=0 or h<=0 or min(x-w/2,y-h/2)<-1e-6 or max(x+w/2,y+h/2)>1+1e-6:raise ValueError(f'Invalid class/box in {label}: {row}')
                counts[names[category]]+=1
        report['splits'][split]=dict(exposures=len(paths),unique_image_sha256=len(unique),negative_exposures=negatives,boxes_by_class=dict(counts))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();report=audit(args.data);destination=Path(args.output);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
