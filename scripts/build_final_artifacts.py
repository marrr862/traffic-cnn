"""Build measured documents after the full experiment; visual QA stays pending."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = Path('/Users/macbook/.cache/codex-runtimes/codex-primary-runtime/dependencies')
PYTHON = BUNDLE/'python/bin/python3'
NODE = BUNDLE/'node/bin/node'
SKILLS = Path('/Users/macbook/.codex/plugins/cache/openai-primary-runtime')


def run(command):
    subprocess.run([str(x) for x in command],cwd=ROOT,check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workflow-pid',type=int,required=True)
    args = parser.parse_args()
    while True:
        status = json.loads((ROOT/'reports/full-workflow-status.json').read_text())
        if status['stage'].startswith('failed'):
            raise RuntimeError(status['stage'])
        if status['stage'] == 'software_and_experiments_complete_document_qa_pending':
            break
        try:
            os.kill(args.workflow_pid,0)
        except ProcessLookupError:
            raise RuntimeError('Experiment workflow exited before completion')
        time.sleep(5)
    report_path = ROOT/'reports/vehicle-finetune-full.json'
    report = json.loads(report_path.read_text())
    rows = list(csv.DictReader((Path(report['training_directory'])/'results.csv').open()))
    cumulative = [float(r['time']) for r in rows]
    durations = [cumulative[i]-(cumulative[i-1] if i else 0) for i in range(len(cumulative))]
    report['epoch_elapsed_seconds'] = durations
    if max(durations) > 4*min(durations):
        report['elapsed_time_note'] = 'Recorded elapsed time includes unusually long interruptions. It does not measure uninterrupted computational throughput; do not compare it directly with pilot training time.'
    report_path.write_text(json.dumps(report,indent=2))
    run([sys.executable,'scripts/make_report.py'])
    run([sys.executable,'scripts/update_status.py'])
    run([PYTHON,'scripts/build_thesis.py'])
    documents = SKILLS/'documents/26.905.11957/skills/documents'
    run([PYTHON,documents/'render_docx.py','thesis/DIPLOMA.docx','--output_dir','thesis/qa-final','--emit_pdf'])
    env = os.environ.copy()
    env.update(RUNTIME_NODE_MODULES=str(BUNDLE/'node/node_modules'),RUNTIME_NODE=str(NODE),RUNTIME_PYTHON=str(PYTHON),RUNTIME_BIN_DIR=str(BUNDLE/'bin/override'))
    subprocess.run([str(NODE),'thesis/.slides-build/build.mjs','DEFENSE'],cwd=ROOT,env=env,check=True)
    slides = SKILLS/'presentations/26.905.11957/skills/presentations'
    subprocess.run([str(PYTHON),str(slides/'container_tools/render_slides.py'),'thesis/presentation/DEFENSE.pptx','--output_dir','thesis/.slides-build/final-render'],cwd=ROOT,env=env,check=True)
    (ROOT/'reports/artifact-status.json').write_text(json.dumps({'stage':'rendered_visual_inspection_pending','docx':str(ROOT/'thesis/DIPLOMA.docx'),'pptx':str(ROOT/'thesis/presentation/DEFENSE.pptx')},indent=2))
    print('Final artifacts rendered; inspect every page and slide before delivery.',flush=True)


if __name__ == '__main__':
    main()
