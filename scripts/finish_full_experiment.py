"""Finish video checks and measured reports after the full training run.

This command does not launch or duplicate training. It waits for the specified
completed report while that training process is alive and fails if it exits
without a report. Logs and status remain on disk.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def status(stage):
    value = dict(stage=stage,updated_unix=time.time())
    p = ROOT/'reports/full-workflow-status.json'
    temporary = p.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2))
    temporary.replace(p)
    print(stage,flush=True)


def execute(command,log):
    with (ROOT/'reports'/log).open('w') as f:
        subprocess.run([sys.executable,*command],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--training-pid',type=int,required=True)
    args = parser.parse_args()
    path = ROOT/'reports/vehicle-finetune-full.json'
    status('waiting_for_full_training')
    while not path.exists():
        try:
            os.kill(args.training_pid,0)
        except ProcessLookupError:
            raise RuntimeError('Training exited without a completed result; inspect train-finetune-full.log')
        time.sleep(5)
    time.sleep(1)
    report = json.loads(path.read_text())
    for name,video,baseline in [('full-baseline','vehicles.mp4',True),('full-continuity','vehicles.mp4',False),('full-second','vehicles-2.mp4',False)]:
        out = ROOT/'outputs'/f'demo-{name}'
        status(f'analyzing_{name}')
        if not (out/'summary.json').exists():
            command = ['-m','traffic_cnn.cli','analyze','--video',str(ROOT/'data/video'/video),'--weights',report['best_weights'],'--output',str(out),'--conf','.3','--device','mps','--imgsz',str(report['imgsz'])]
            if video == 'vehicles.mp4':
                command.extend(['--line','0','1296','3839','1296'])
            if baseline:
                command.append('--baseline-tracking')
            else:
                command.append('--continuity-tracking')
            execute(command,f'video-{name}.log')
        if video == 'vehicles.mp4':
            execute(['scripts/evaluate_counting.py','--results',str(out),'--name',name],f'counting-{name}.log')
    status('building_reports')
    import cv2
    capture = cv2.VideoCapture(str(ROOT/'outputs/demo-full-continuity/annotated.mp4'))
    capture.set(cv2.CAP_PROP_POS_FRAMES,200)
    ok,frame = capture.read()
    capture.release()
    if not ok or not cv2.imwrite(str(ROOT/'reports/demo-full-frame.jpg'),frame):
        raise RuntimeError('Cannot create full-model video preview')
    execute(['scripts/make_report.py'],'make-report-final.log')
    execute(['-m','unittest','discover','-s','tests','-v'],'tests-final.log')
    sources = [*ROOT.glob('*.py'),*ROOT.glob('*.toml'),*ROOT.glob('*.txt'),*(ROOT/'traffic_cnn').glob('*.py'),*(ROOT/'scripts').glob('*.py'),*(ROOT/'tests').glob('*.py'),*(ROOT/'configs').glob('*.yaml')]
    hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    hashes.update({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'runs/experiments').glob('vehicle-*/weights/best.pt')})
    (ROOT/'reports/final-integrity.json').write_text(json.dumps(hashes,indent=2))
    status('software_and_experiments_complete_document_qa_pending')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        status('failed: '+str(exc))
        raise
