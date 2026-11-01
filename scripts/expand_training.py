"""Training-only augmentation with equal-exposure control; no new independent scenes."""
import json
import hashlib
from pathlib import Path
import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]


def augment(image, rows, seed):
    rng = np.random.default_rng(seed)
    result = cv2.flip(image,1)
    labels = []
    for row in rows:
        parts = row.split()
        parts[1] = f'{1-float(parts[1]):.8f}'
        labels.append(' '.join(parts))
    gain = rng.uniform(.75,1.2)
    offset = rng.uniform(-18,18)
    result = np.clip(result.astype(np.float32)*gain+offset,0,255).astype(np.uint8)
    if seed % 3 == 0:
        result = cv2.GaussianBlur(result,(3,3),.7)
    return result,labels


def main():
    source = ROOT/'data/visdrone-vehicles'
    originals = [Path(p) for p in (source/'pilot-train.txt').read_text().splitlines() if p]
    heldout = {r['sha256'] for split in ['val','test'] for r in json.loads((source/f'{split}-manifest.json').read_text())}
    images,labels = source/'images/train-expanded',source/'labels/train-expanded'
    images.mkdir(exist_ok=True);labels.mkdir(exist_ok=True)
    variants,manifest = [],[]
    for index,path in enumerate(originals):
        assert path.parent == source/'images/train',path
        original_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert original_digest not in heldout,path
        rows = (source/'labels/train'/path.with_suffix('.txt').name).read_text().splitlines()
        image = cv2.imread(str(path))
        if image is None:raise ValueError(f'Cannot decode {path}')
        variant,converted = augment(image,rows,42+index)
        destination = images/f'aug-{path.name}'
        if not cv2.imwrite(str(destination),variant,[cv2.IMWRITE_JPEG_QUALITY,95]):raise ValueError(destination)
        (labels/destination.with_suffix('.txt').name).write_text('\n'.join(converted)+ ('\n' if converted else ''))
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        assert digest not in heldout
        variants.append(destination)
        manifest.append(dict(file=str(destination.relative_to(source)),source=str(path.relative_to(source)),source_sha256=original_digest,sha256=digest,seed=42+index,boxes=len(converted)))
    for name,paths in [('augmentation-control',originals+originals),('augmentation-expanded',originals+variants)]:
        listing = source/f'{name}-train.txt'
        listing.write_text('\n'.join(map(str,paths))+'\n')
        config = yaml.safe_load((ROOT/'configs/visdrone-vehicles.yaml').read_text())
        config['train'] = str(listing)
        (ROOT/'configs'/f'{name}.yaml').write_text(yaml.safe_dump(config,sort_keys=False))
    full_originals = sorted((source/'images/train').glob('*.jpg'))
    full_listing = source/'augmentation-full-train.txt'
    full_listing.write_text('\n'.join(map(str,full_originals+variants))+'\n')
    config = yaml.safe_load((ROOT/'configs/visdrone-vehicles.yaml').read_text())
    config['train'] = str(full_listing)
    (ROOT/'configs/visdrone-expanded-full.yaml').write_text(yaml.safe_dump(config,sort_keys=False))
    report = dict(full_original_images=len(full_originals),full_expanded_images=len(full_originals)+len(variants),original_images=len(originals),generated_variants=len(variants),training_exposures_each=len(originals)*2,independent_scenes_added=0,heldout_unchanged=True,transformations=['horizontal flip with corrected x center','brightness/contrast','mild Gaussian blur on every third image'],manifest=manifest)
    (ROOT/'reports/training-expansion.json').write_text(json.dumps(report,indent=2))
    print({k:v for k,v in report.items() if k!='manifest'})


if __name__=='__main__':main()
