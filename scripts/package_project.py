"""Create a portable submission bundle, excluding data archives and runtimes."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    required = [ROOT/'reports/vehicle-finetune-full.json',ROOT/'thesis/DIPLOMA.docx',ROOT/'thesis/presentation/DEFENSE.pptx',ROOT/'outputs/demo-full-continuity/summary.json']
    if not all(p.is_file() for p in required):
        raise RuntimeError('Finish experiments and final documents before packaging')
    files = set()
    for pattern in ['*.md','*.toml','*.txt','*.py','*.command','.gitignore']:
        files.update(p for p in ROOT.glob(pattern) if p.is_file())
    for folder in ['traffic_cnn','scripts','tests','configs']:
        files.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files.update((ROOT/'reports').glob('*.json'))
    files.update((ROOT/'reports').glob('*.md'))
    files.update((ROOT/'reports').glob('*.png'))
    files.update((ROOT/'reports').glob('*.jpg'))
    files.update(p for p in (ROOT/'reports').glob('*.log') if p.name.startswith(('train-','counting-','tests-','video-full','download-verified')))
    files.update(p for p in (ROOT/'thesis').glob('*.md'))
    files.update(required[1:3])
    files.add(ROOT/'thesis/.slides-build/build.mjs')
    files.update((ROOT/'data/video').glob('*.mp4'))
    files.update((ROOT/'data/visdrone-vehicles').glob('*-manifest.json'))
    files.add(ROOT/'data/visdrone-vehicles/pilot-train.txt')
    for experiment in (ROOT/'runs/experiments').glob('vehicle-*'):
        files.update(p for p in experiment.glob('*') if p.is_file() and p.suffix in ['.png','.csv','.yaml'])
        files.add(experiment/'weights/best.pt')
    for output in (ROOT/'outputs').glob('demo-full*'):
        files.update(p for p in output.glob('*') if p.is_file() and p.name not in ['progress.tmp'])
    files = sorted(p for p in files if p.is_file())
    manifest = {}
    for p in files:
        checksum = hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):
                checksum.update(block)
        manifest[str(p.relative_to(ROOT))] = {'sha256':checksum.hexdigest(),'bytes':p.stat().st_size}
    destination = ROOT/'deliverables'
    destination.mkdir(exist_ok=True)
    archive = destination/'traffic-cnn-thesis.zip'
    temporary = archive.with_suffix('.tmp')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for p in files:
            z.write(p,Path('traffic-cnn')/p.relative_to(ROOT))
        z.writestr('traffic-cnn/BUNDLE_MANIFEST.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(temporary) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f'Bundle CRC failed: {bad}')
    temporary.replace(archive)
    print(json.dumps({'archive':str(archive),'files':len(files),'bytes':archive.stat().st_size},indent=2))


if __name__ == '__main__':
    main()
