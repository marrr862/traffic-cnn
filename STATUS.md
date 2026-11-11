# Состояние дипломного проекта

Python-приложение: CNN YOLOv8s / YOLOv8n, ByteTrack, подсчет пересечений по одной или нескольким линиям, скорость в км/ч по гомографической калибровке дороги, плотность и уровень обслуживания (LOS A–F), тепловая карта, экспорт CSV/JSON и локальный интерфейс Streamlit на армянском языке.

Репозиторий: https://github.com/marrr862/traffic-cnn

## Данные

VisDrone2019-DET: train 6469, validation 547, test 1610 изображений; 218242 рамки train. Три точных повтора исключены, архивы проверены по SHA-256. Расширенный набор: +1024 аугментированных изображения.

MIO-TCD Localization (дорожные камеры, CC BY-NC-SA 4.0): разбиение по sha256(image_id) — 85% train (подвыборка 30000), 5% val, 10% test; класс motorized_vehicle маскируется.

UA-DETRAC: только внешняя проверка подсчета, обучение не проводилось.

Пять классов транспорта: car, van, truck, bus, motorcycle.

## Завершенные обучения

Test mAP — на test-части собственного набора данных запуска (поэтому строки с разными наборами не сравниваются напрямую; сравнение моделей на одинаковых данных — в README.md и reports/EXPERIMENT_REPORT.md).

| Запуск | Данные | Вход | Эпох | Test mAP50 | Test mAP50–95 |
|---|---|---:|---:|---:|---:|
| vehicle-augmentation-control | augmentation-control | 640 | 3 | 0.3385 | 0.1978 |
| vehicle-augmentation-expanded | augmentation-expanded | 640 | 3 | 0.3363 | 0.1972 |
| vehicle-expanded-full | visdrone-expanded-full | 640 | 3 | 0.3470 | 0.2050 |
| vehicle-finetune-full | visdrone-vehicles | 640 | 10 | 0.3441 | 0.2029 |
| vehicle-finetune-pilot | visdrone-pilot | 416 | 15 | 0.1384 | 0.0686 |
| vehicle-hires-960 | visdrone-expanded-full | 960 | 15 | 0.4594 | 0.2859 |
| vehicle-road-combined | combined-road | 640 | 8 | 0.4760 | 0.3228 |
| vehicle-road-yolov8s | combined-road | 640 | 8 | 0.5255 | 0.3610 |
| **vehicle-road-yolov8s-long** (рекомендуемая; продолжение vehicle-road-yolov8s, lr0 0.0005) | combined-road | 640 | 12 | 0.5565 | 0.3845 |
| vehicle-scratch-pilot | visdrone-pilot | 416 | 15 | 0.0262 | 0.0087 |

Все запуски: seed 42, Apple M4, 16 ГБ, MPS. Лучшая эпоха выбирается по validation. Часть операций MPS недетерминирована.

Обученные веса четырех основных моделей (vehicle-road-yolov8s-long, vehicle-road-yolov8s, vehicle-road-combined, vehicle-hires-960) и демонстрационные видео скачиваются командой `python scripts/download_assets.py` (релиз v1.0 на GitHub).

## Проверки и материалы

73 автоматических проверок (`python -m unittest discover -s tests`) охватывают геометрию, калибровку, смену ID, соседние машины, тайлинг, преобразование разметки, сопоставление событий, источники видео, интерфейс и обработку видео. Проверки, требующие локальных весов или результатов, пропускаются при их отсутствии. Точность CNN определяется отдельными экспериментами.

Интерфейс: http://127.0.0.1:8501. Запуск: run_app.command. Инструкции: README.md, QUICKSTART.md. Метрики: reports/EXPERIMENT_REPORT.md, reports/DETRAC_RESULTS.md, reports/RESOLUTION_RESULTS.md. Текст: thesis/DIPLOMA.docx. Презентация: thesis/presentation/DEFENSE.pptx. Материал выступления: thesis/DEFENSE_NOTES.md.

## Что осталось

- thesis/DIPLOMA.docx обновлён 7 ноября: текст на армянском (thesis/hy/*.md → scripts/build_thesis_hy.py), рекомендуемая модель vehicle-road-yolov8s-long, MIO-TCD, тайлинг, скорость, плотность/LOS, UA-DETRAC, проверка ускоренного видео. Русская версия от 10 октября — thesis/archive/. Презентация thesis/presentation/DEFENSE.pptx обновлена 11 ноября: 12 слайдов на армянском для доклада на 10 минут, текст выступления в заметках (scripts/build_defense_hy.js). Старая русская версия — thesis/archive/.
- Титульные сведения и требования кафедры не предоставлены.
- Разметка подсчета для демонстрационных роликов предварительная и требует независимой проверки человеком.

## Ограничения

Скорость и плотность корректны настолько, насколько корректна калибровка (плоская дорога, неподвижная камера). Смена ID может давать двойной подсчет. Первый ролик использован при разработке; второй без разметки проверяет исполнение, а не точность. Точные дубликаты удалены, но похожие сцены и независимость камер не проверены полностью. Один seed и ограниченный бюджет эпох не устанавливают надежность или максимальные возможности модели.
