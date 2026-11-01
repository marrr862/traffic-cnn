"""Adapt a copied project to its new root without retraining models."""
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main(root=ROOT):
    root = Path(root).resolve()
    for path in (root/'reports').glob('vehicle-*.json'):
        report = json.loads(path.read_text())
        old_root = Path(report['data']).parent.parent
        if old_root != root:
            report.setdefault('original_project_root',str(old_root))
        for key in ['data','best_weights','training_directory']:
            report[key] = str(root/Path(report[key]).relative_to(old_root))
        path.write_text(json.dumps(report,indent=2))
    for name in ['visdrone-vehicles.yaml','visdrone-pilot.yaml','augmentation-control.yaml','augmentation-expanded.yaml','visdrone-expanded-full.yaml']:
        path = root/'configs'/name
        if path.exists():
            data = yaml.safe_load(path.read_text())
            old_data = Path(data['path'])
            data['path'] = str(root/'data/visdrone-vehicles')
            for split in ['train','val','test']:
                value = Path(data[split])
                if value.is_absolute() and value.is_relative_to(old_data):
                    data[split] = str(Path(data['path'])/value.relative_to(old_data))
            if name in ['visdrone-pilot.yaml','augmentation-control.yaml','augmentation-expanded.yaml','visdrone-expanded-full.yaml']:
                manifest = Path(data['train'])
                if manifest.is_file():
                    values = [Path(line) for line in manifest.read_text().splitlines() if line]
                    manifest.write_text('\n'.join(str(Path(data['path'])/p.relative_to(old_data)) if p.is_relative_to(old_data) else str(p) for p in values)+'\n')
            path.write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False))
    for path in (root/'outputs').glob('**/summary.json'):
        report = json.loads(path.read_text())
        old_parts = Path(report['weights']).parts
        if 'runs' in old_parts:
            report['weights'] = str(root/Path(*old_parts[old_parts.index('runs'):]))
            if 'source_video' in report:
                source_parts = Path(report['source_video']).parts
                if 'data' in source_parts:
                    report['source_video'] = str(root/Path(*source_parts[source_parts.index('data'):]))
                elif 'outputs' in source_parts:
                    report['source_video'] = str(root/Path(*source_parts[source_parts.index('outputs'):]))
            path.write_text(json.dumps(report,indent=2))
    recommendation = root/'reports/recommended-model.json'
    if recommendation.exists():
        report = json.loads(recommendation.read_text())
        parts = Path(report['weights']).parts
        if 'runs' in parts:
            report['weights'] = str(root/Path(*parts[parts.index('runs'):]))
            recommendation.write_text(json.dumps(report,indent=2))
    print(f'Project paths updated for {root}')


if __name__ == '__main__':
    main()
