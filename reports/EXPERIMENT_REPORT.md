# Эксперименты обучения CNN на транспортном корпусе

Источник: [VisDrone2019-DET](https://github.com/VisDrone/VisDrone-Dataset).
Официальные train/val/test-dev; исходная разметка адаптирована к пяти классам транспорта.
Съемка с дрона; результаты не доказывают качество на стационарной камере.

## Подготовленные данные

| Выборка | Изображений | Рамок транспорта |
|---|---:|---:|
| test | 1610 | 45289 |
| val | 547 | 21917 |
| train | 6469 | 218242 |

Для первого запуска использованы 1024 тренировочных изображений (seed 42); val и test сохранены полностью.
Исключено точных дубликатов: 3.

## Результаты

| Эксперимент | Эпох в запуске | Инициализация | Тест precision | Тест recall | Тест mAP50 | Тест mAP50–95 | Время обучения, мин |
|---|---:|---|---:|---:|---:|---:|---:|
| vehicle-augmentation-control | 3 | local-checkpoint | 0.4669 | 0.3522 | 0.3385 | 0.1978 | 4.89 |
| vehicle-augmentation-expanded | 3 | local-checkpoint | 0.4533 | 0.3518 | 0.3363 | 0.1972 | 5.77 |
| vehicle-expanded-full | 3 | local-checkpoint | 0.4761 | 0.3580 | 0.3470 | 0.2050 | 17.99 |
| vehicle-finetune-full | 10 | COCO-pretrained | 0.4607 | 0.3583 | 0.3441 | 0.2029 | 69.13 |
| vehicle-finetune-pilot | 15 | COCO-pretrained | 0.2559 | 0.1942 | 0.1384 | 0.0686 | 8.84 |
| vehicle-scratch-pilot | 15 | random | 0.4878 | 0.0378 | 0.0262 | 0.0087 | 7.79 |

Веса vehicle-augmentation-control: `/Users/macbook/Downloads/FakeNewsNet-master/traffic-cnn/runs/experiments/vehicle-augmentation-control/weights/best.pt`.
Веса vehicle-augmentation-expanded: `/Users/macbook/Downloads/FakeNewsNet-master/traffic-cnn/runs/experiments/vehicle-augmentation-expanded/weights/best.pt`.
Веса vehicle-expanded-full: `/Users/macbook/Downloads/FakeNewsNet-master/traffic-cnn/runs/experiments/vehicle-expanded-full/weights/best.pt`.
Веса vehicle-finetune-full: `/Users/macbook/Downloads/FakeNewsNet-master/traffic-cnn/runs/experiments/vehicle-finetune-full/weights/best.pt`.
Веса vehicle-finetune-pilot: `/Users/macbook/Downloads/FakeNewsNet-master/traffic-cnn/runs/experiments/vehicle-finetune-pilot/weights/best.pt`.
Веса vehicle-scratch-pilot: `/Users/macbook/Downloads/FakeNewsNet-master/traffic-cnn/runs/experiments/vehicle-scratch-pilot/weights/best.pt`.

Длительность основного запуска включает длительные перерывы. Это время завершения процесса, а не непрерывная вычислительная производительность; прямое сравнение с pilot некорректно.

## Предварительная проверка подсчета

| Модель | Событий | Визуальный ориентир | Совпадений по интервалам | Непокрытых интервалов | Лишних событий |
|---|---:|---:|---:|---:|---:|
| finetune-tracking-v2 | 10 | 10 | 9 | 1 | 1 |
| finetune | 10 | 10 | 9 | 1 | 1 |
| full-baseline | 10 | 10 | 9 | 1 | 1 |
| full-continuity | 9 | 10 | 8 | 2 | 1 |
| practical-flow | 10 | 10 | 9 | 1 | 1 |
| scratch | 11 | 10 | 10 | 0 | 1 |

Ориентир размечен ассистентом по контактным листам до просмотра предсказаний и требует подтверждения человеком. Один короткий ролик не определяет общую точность подсчета. Временное сопоставление использует приблизительные интервалы и допуск 6 кадров. У исходной пилотной дообученной модели общий счет 10 совпадает с ориентиром, однако найдено одно непокрытое событие и одно событие вне интервалов; равенство общего счета скрывает компенсацию ошибок. Значения времени обработки записаны в условиях текущего запуска; для сравнения быстродействия нужен отдельный замер при одинаковой нагрузке.

## Границы выводов

- Продолжения из local-checkpoint включают предыдущее обучение весов; число эпох в таблице относится только к текущему запуску.
- Результаты аугментации и одинакового бюджета описаны отдельно в reports/AUGMENTATION_RESULTS.md. Полный расширенный запуск не отделяет эффект дополнительных эпох от аугментации.
- Pilot использует 1024 изображения; full использует весь train. Разные данные и размеры входа не позволяют приписать изменение качества только инициализации.
- Оценка YOLO не маскирует исходные игнорируемые области и не является официальным баллом VisDrone.
- Один seed не дает оценку вариативности обучения; некоторые операции MPS недетерминированы.
- Precision/recall приведены по библиотечному протоколу оценки, а не при фиксированном пороге интерфейса 0.3.
- При нулевой полноте высокая precision отдельных редких классов не подтверждает полезное обнаружение.
- Оценка обнаружения не заменяет проверку точности подсчета по вручную размеченным видео.
- Порог интерфейса не использовался для подбора тестовых результатов.

## Воспроизведение

Команды, параметры, результаты по классам и версии сохранены в README, reports/vehicle-*.json и runs/experiments/*/args.yaml.
