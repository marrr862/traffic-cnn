#!/bin/zsh
# Runs after vehicle-road-combined finishes: evaluation, then YOLOv8s training on the same data.
cd "$(dirname "$0")/.."
while [ ! -f reports/vehicle-road-combined.json ]; do sleep 60; done
.venv/bin/python scripts/evaluate_road_models.py --models vehicle-hires-960,vehicle-road-combined > reports/road-eval.log 2>&1
.venv/bin/python scripts/evaluate_detrac.py --sequence MVI_39031 --device mps --models vehicle-finetune-full:640,vehicle-expanded-full:960,vehicle-hires-960:960,vehicle-road-combined:640,vehicle-road-combined:960 > reports/road-detrac.log 2>&1
caffeinate -i .venv/bin/python scripts/run_experiment.py --name vehicle-road-yolov8s --data configs/combined-road.yaml --weights yolov8s.pt --optimizer AdamW --lr0 0.001 --epochs 8 --imgsz 640 --batch 16 --device mps > reports/train-vehicle-road-yolov8s.log 2>&1
.venv/bin/python scripts/evaluate_road_models.py --models vehicle-road-yolov8s > reports/road-eval-v8s.log 2>&1
.venv/bin/python scripts/evaluate_detrac.py --sequence MVI_39031 --device mps --models vehicle-finetune-full:640,vehicle-expanded-full:960,vehicle-hires-960:960,vehicle-road-combined:640,vehicle-road-combined:960,vehicle-road-yolov8s:640,vehicle-road-yolov8s:960 > reports/road-detrac-v8s.log 2>&1
echo done > reports/road-pipeline.done
