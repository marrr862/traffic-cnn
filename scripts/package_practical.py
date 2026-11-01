"""Package the practical software, trained weights and demonstrations only."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = set()
    for name in ['app.py','pyproject.toml','requirements.txt','requirements-lock.txt','run_app.command','README.md','QUICKSTART.md','ARCHITECTURE.md','EXPERIMENTS.md']:
        path = ROOT/name
        if path.exists():
            files.add(path)
    for folder in ['traffic_cnn','tests','configs']:
        files.update(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for name in ['download_data.py','prepare_visdrone.py','run_experiment.py','evaluate_counting.py','rebase_paths.py','make_report.py','plot_dataset.py','preview_predictions.py','package_practical.py','verify_practical.py','expand_training.py','run_augmentation_comparison.py','report_augmentation.py','audit_dataset.py','dataset_diagnostics.py','compare_resolution.py','report_resolution.py','download_detrac.py','evaluate_detrac.py','report_detrac.py']:
        files.add(ROOT/'scripts'/name)
    files.update(p for p in (ROOT/'reports').glob('*') if p.is_file() and p.suffix in ['.json','.md','.png','.jpg'] and p.name not in ['artifact-status.json','full-workflow-status.json','final-integrity.json'])
    files.update((ROOT/'reports').glob('tests-practical*.log'))
    files.add(ROOT/'reports/portable-bundle-check.log')
    files.update((ROOT/'reports').glob('*clean*.log'))
    files.update((ROOT/'reports').glob('requirements-*-macos.txt'))
    files.update((ROOT/'data/ua-detrac').glob('MVI_*/annotations.xml'))
    files.update((ROOT/'data/ua-detrac').glob('MVI_*/manifest.json'))
    files.update((ROOT/'data/video').glob('*.mp4'))
    files.update((ROOT/'data/visdrone-vehicles').glob('*-manifest.json'))
    files.update((ROOT/'data/visdrone-vehicles').glob('*-train.txt'))
    for directory in (ROOT/'runs/experiments').glob('vehicle-*'):
        files.add(directory/'weights/best.pt')
        files.update(p for p in directory.glob('*') if p.is_file() and p.suffix in ['.csv','.yaml','.png'])
    for pattern in ['practical-*','demo-full*']:
        for directory in (ROOT/'outputs').glob(pattern):
            files.update(p for p in directory.glob('*') if p.is_file() and p.suffix in ['.mp4','.csv','.json','.yaml'])
    files = sorted(p for p in files if p.is_file())
    manifest = {}
    # Read in chunks to support Python 3.10 and avoid loading videos into memory.
    for path in files:
        checksum = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''):
                checksum.update(chunk)
        manifest[str(path.relative_to(ROOT))] = dict(bytes=path.stat().st_size,sha256=checksum.hexdigest())
    destination = ROOT/'deliverables/traffic-cnn-practical.zip'
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary = destination.with_suffix('.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as archive:
        for path in files:
            archive.write(path,Path('traffic-cnn')/path.relative_to(ROOT))
        archive.writestr('traffic-cnn/BUNDLE_MANIFEST.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('Practical bundle CRC check failed')
        if any(name.endswith(('.docx','.pptx')) for name in archive.namelist()):
            raise RuntimeError('Unexpected document in practical bundle')
    temporary.replace(destination)
    print(json.dumps(dict(archive=str(destination),files=len(files),bytes=destination.stat().st_size),indent=2))


if __name__ == '__main__':
    main()
