"""Convert official VisDrone DET archives to five vehicle classes.

Only consumes downloaded archives; never executes dataset-provided scripts.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import random
import zipfile
from PIL import Image
import yaml

NAMES = {0:'car', 1:'van', 2:'truck', 3:'bus', 4:'motorcycle'}
CLASS_MAP = {4:0, 5:1, 6:2, 9:3, 10:4}
ROOT = Path(__file__).resolve().parents[1]

def prepare(pilot_size=1024):
    target = ROOT/'data/visdrone-vehicles'
    report = {'source':'https://github.com/VisDrone/VisDrone-Dataset',
              'mirror':'https://github.com/ultralytics/assets/releases/download/v0.0.0/',
              'classes':NAMES, 'splits':{}, 'archive_sha256':{}, 'duplicates_excluded':[],
              'metric_protocol':'Vehicle-only YOLO evaluation; ignored regions not masked. Not an official VisDrone challenge score.'}
    seen = {}
    # Priority preserves test, then val, and excludes any exact duplicate from train.
    for source_split,split in [('test-dev','test'),('val','val'),('train','train')]:
        archive = ROOT/f'data/archives/VisDrone2019-DET-{source_split}.zip'
        report['archive_sha256'][source_split] = sha256(archive.read_bytes()).hexdigest()
        images = target/'images'/split
        labels = target/'labels'/split
        images.mkdir(parents=True,exist_ok=True)
        labels.mkdir(parents=True,exist_ok=True)
        counts, skipped, negatives, manifest = Counter(), Counter(), 0, []
        with zipfile.ZipFile(archive) as z:
            bad = z.testzip()
            if bad:
                raise ValueError(f'Corrupt archive member: {bad}')
            members = set(z.namelist())
            for member in sorted(m for m in members if '/images/' in m and m.lower().endswith('.jpg')):
                name = Path(member).name
                annotation = member.replace('/images/','/annotations/').rsplit('.',1)[0]+'.txt'
                if annotation not in members:
                    raise ValueError(f'Missing annotation: {annotation}')
                payload = z.read(member)
                digest = sha256(payload).hexdigest()
                if digest in seen:
                    report['duplicates_excluded'].append({'split':split,'file':name,'duplicate_of':seen[digest]})
                    continue
                seen[digest] = f'{split}/{name}'
                destination = images/name
                destination.write_bytes(payload)
                with Image.open(destination) as image:
                    image.verify()
                with Image.open(destination) as image:
                    w,h = image.size
                converted = []
                for row in z.read(annotation).decode('utf-8-sig').strip().splitlines():
                    fields = row.split(',')
                    x,y,bw,bh = map(float,fields[:4])
                    score,cls = int(fields[4]),int(fields[5])
                    if score == 0 or cls not in CLASS_MAP:
                        skipped['ignored' if score == 0 else 'non_vehicle'] += 1
                        continue
                    x1,y1 = max(0,x),max(0,y)
                    x2,y2 = min(w,x+bw),min(h,y+bh)
                    if x2 <= x1 or y2 <= y1:
                        skipped['invalid_box'] += 1
                        continue
                    cls_out = CLASS_MAP[cls]
                    values = ((x1+x2)/(2*w),(y1+y2)/(2*h),(x2-x1)/w,(y2-y1)/h)
                    assert all(0 <= v <= 1 for v in values)
                    converted.append(f'{cls_out} '+' '.join(f'{v:.8f}' for v in values))
                    counts[NAMES[cls_out]] += 1
                (labels/Path(name).with_suffix('.txt')).write_text('\n'.join(converted)+('\n' if converted else ''))
                negatives += not converted
                manifest.append({'file':name,'sha256':digest,'boxes':len(converted),'scene_prefix':name.split('_')[0]})
        report['splits'][split] = {'images':len(manifest),'boxes_by_class':dict(counts),
                                   'negative_images':negatives,'skipped_annotations':dict(skipped)}
        (target/f'{split}-manifest.json').write_text(json.dumps(manifest,indent=2))
        print(split,report['splits'][split],flush=True)
    config = {'path':str(target),'train':'images/train','val':'images/val','test':'images/test','names':NAMES}
    (ROOT/'configs/visdrone-vehicles.yaml').write_text(yaml.safe_dump(config,sort_keys=False))
    # Scene-diverse subset for the first local experiment; keep full official val/test.
    files = sorted((target/'images/train').glob('*.jpg'))
    groups = {}
    for path in files:
        groups.setdefault(path.stem.split('_')[0],[]).append(path)
    rng = random.Random(42)
    keys = sorted(groups)
    rng.shuffle(keys)
    for values in groups.values():
        rng.shuffle(values)
    chosen = []
    while len(chosen) < min(pilot_size,len(files)):
        for key in keys:
            if groups[key] and len(chosen) < min(pilot_size,len(files)):
                chosen.append(groups[key].pop())
    pilot = target/'pilot-train.txt'
    pilot.write_text('\n'.join(str(p) for p in chosen)+'\n')
    config['train'] = str(pilot)
    (ROOT/'configs/visdrone-pilot.yaml').write_text(yaml.safe_dump(config,sort_keys=False))
    report['pilot'] = {'images':len(chosen),'seed':42,'selection':'Round-robin filename prefixes within official train; all official val/test retained.',
                       'boxes_by_class':dict(Counter(NAMES[int(row.split()[0])] for p in chosen for row in (target/'labels/train'/p.with_suffix('.txt').name).read_text().splitlines()))}
    report['limitations'] = ['Drone viewpoint differs from a fixed roadside camera.',
                            'Exact duplicate hashes checked; near duplicates and camera identity across official splits are not verified.',
                            'Ignored regions omitted from labels, not masked during training/evaluation.',
                            'Pilot subset is not full-data training.']
    (ROOT/'reports/dataset.json').write_text(json.dumps(report,indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot-size',type=int,default=1024)
    args = parser.parse_args()
    if args.pilot_size <= 0:
        parser.error('pilot-size must be positive')
    prepare(args.pilot_size)
