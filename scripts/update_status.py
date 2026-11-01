import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
runs = [json.loads(p.read_text()) for p in sorted((ROOT/'reports').glob('vehicle-*.json'))]
recommended_path = ROOT/'reports/recommended-model.json'
recommended = json.loads(recommended_path.read_text())['name'] if recommended_path.exists() else None
# Count tests the same way CI does, so the number in STATUS.md never goes stale.
listing = subprocess.run([sys.executable,'-c','import unittest;s=unittest.defaultTestLoader.discover("tests");print(s.countTestCases())'],cwd=ROOT,capture_output=True,text=True)
test_count = listing.stdout.strip() or '?'
lines = ['# Состояние дипломного проекта','',
         'Python-приложение: CNN YOLOv8s / YOLOv8n, ByteTrack, подсчет пересечений по одной или нескольким линиям, скорость в км/ч по гомографической калибровке дороги, плотность и уровень обслуживания (LOS A–F), тепловая карта, экспорт CSV/JSON и локальный интерфейс Streamlit на армянском языке.','',
         'Репозиторий: https://github.com/marrr862/traffic-cnn','',
         '## Данные','',
         'VisDrone2019-DET: train 6469, validation 547, test 1610 изображений; 218242 рамки train. Три точных повтора исключены, архивы проверены по SHA-256. Расширенный набор: +1024 аугментированных изображения.', '',
         'MIO-TCD Localization (дорожные камеры, CC BY-NC-SA 4.0): разбиение по sha256(image_id) — 85% train (подвыборка 30000), 5% val, 10% test; класс motorized_vehicle маскируется.', '',
         'UA-DETRAC: только внешняя проверка подсчета, обучение не проводилось.', '',
         'Пять классов транспорта: car, van, truck, bus, motorcycle.', '',
         '## Завершенные обучения','',
         'Test mAP — на test-части собственного набора данных запуска (поэтому строки с разными наборами не сравниваются напрямую; сравнение моделей на одинаковых данных — в README.md и reports/EXPERIMENT_REPORT.md).', '',
         '| Запуск | Данные | Вход | Эпох | Test mAP50 | Test mAP50–95 |','|---|---|---:|---:|---:|---:|']
for r in runs:
    name = f"**{r['name']}** (рекомендуемая)" if r['name'] == recommended else r['name']
    lines.append(f"| {name} | {Path(r['data']).stem} | {r['imgsz']} | {r['epochs_completed']} | {r['test']['metrics/mAP50(B)']:.4f} | {r['test']['metrics/mAP50-95(B)']:.4f} |")
lines.extend(['', 'Все запуски: seed 42, Apple M4, 16 ГБ, MPS. Лучшая эпоха выбирается по validation. Часть операций MPS недетерминирована.', '',
              'Обученные веса трех основных моделей (vehicle-road-yolov8s, vehicle-road-combined, vehicle-hires-960) и демонстрационные видео скачиваются командой `python scripts/download_assets.py`.', '',
              '## Проверки и материалы','',
              f'{test_count} автоматических проверок (`python -m unittest discover -s tests`) охватывают геометрию, калибровку, смену ID, соседние машины, тайлинг, преобразование разметки, сопоставление событий, источники видео, интерфейс и обработку видео. Проверки, требующие локальных весов или результатов, пропускаются при их отсутствии. GitHub Actions запускает проверки при каждом push. Точность CNN определяется отдельными экспериментами.', '',
              'Интерфейс: http://127.0.0.1:8501. Запуск: run_app.command. Инструкции: README.md, QUICKSTART.md. Метрики: reports/EXPERIMENT_REPORT.md, reports/DETRAC_RESULTS.md, reports/RESOLUTION_RESULTS.md. Текст: thesis/DIPLOMA.docx. Презентация: thesis/presentation/DEFENSE.pptx. Материал выступления: thesis/DEFENSE_NOTES.md.', '',
              '## Что осталось','',
              '- thesis/DIPLOMA.docx и thesis/presentation/DEFENSE.pptx собраны 10 октября и описывают модель vehicle-finetune-full (test mAP50 0,34). Их нужно обновить под текущую рекомендуемую модель, MIO-TCD, тайлинг, скорость в км/ч и проверку на UA-DETRAC.',
              '- Титульные сведения и требования кафедры не предоставлены.',
              '- Разметка подсчета для демонстрационных роликов предварительная и требует независимой проверки человеком.', '',
              '## Ограничения','',
              'Скорость и плотность корректны настолько, насколько корректна калибровка (плоская дорога, неподвижная камера). Смена ID может давать двойной подсчет. Первый ролик использован при разработке; второй без разметки проверяет исполнение, а не точность. Точные дубликаты удалены, но похожие сцены и независимость камер не проверены полностью. Один seed и ограниченный бюджет эпох не устанавливают надежность или максимальные возможности модели.'])
(ROOT/'STATUS.md').write_text('\n'.join(lines)+'\n')
