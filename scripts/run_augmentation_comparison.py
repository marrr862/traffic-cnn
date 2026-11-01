"""Two matched short continuation runs, selected by validation rather than test."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    weights=ROOT/'runs/experiments/vehicle-finetune-full/weights/best.pt'
    names=['vehicle-augmentation-control','vehicle-augmentation-expanded']
    if any((ROOT/f'reports/{name}.json').exists() or (ROOT/f'runs/experiments/{name}').exists() for name in names):
        raise ValueError('Comparison names already exist. Use new experiment names; existing logs and results are preserved.')
    for name,config in zip(names,['augmentation-control','augmentation-expanded']):
        with (ROOT/f'reports/train-{name}.log').open('w') as log:
            subprocess.run([sys.executable,str(ROOT/'scripts/run_experiment.py'),'--name',name,'--data',f'configs/{config}.yaml','--weights',str(weights),'--epochs','3','--imgsz','640','--batch','8','--device','mps','--optimizer','AdamW','--lr0','0.0001'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    reports=[json.loads((ROOT/f'reports/{name}.json').read_text()) for name in names]
    baseline=json.loads((ROOT/'reports/vehicle-finetune-full.json').read_text())
    key='metrics/mAP50-95(B)'
    selected=max([baseline,*reports],key=lambda r:r['validation'][key])
    comparison=dict(protocol='Exploratory matched 3-epoch continuation from the same full checkpoint, 2048 examples per epoch, seed 42. Control repeats 1024 original training images; expanded uses originals plus 1024 transformed variants. Online augmentations remain identical. No independent scenes added. Test has been used in prior experiments, not a new blind holdout.',selected_by_validation=selected['name'],baseline={s:baseline[s] for s in ['validation','test']},runs={r['name']:{s:r[s] for s in ['validation','test']} for r in reports},validation_delta_expanded_minus_control=reports[1]['validation'][key]-reports[0]['validation'][key],test_delta_expanded_minus_control=reports[1]['test'][key]-reports[0]['test'][key])
    (ROOT/'reports/augmentation-comparison.json').write_text(json.dumps(comparison,indent=2))
    print(json.dumps(comparison,indent=2))


if __name__=='__main__':main()
