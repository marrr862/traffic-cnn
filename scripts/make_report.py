"""Build a grounded report and publication-ready static comparison chart."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def main():
    dataset=json.loads((ROOT/'reports/dataset.json').read_text())
    runs=[json.loads(p.read_text()) for p in sorted((ROOT/'reports').glob('vehicle-*.json'))]
    lines=['# Эксперименты обучения CNN на транспортном корпусе','',
           'Источник: [VisDrone2019-DET](https://github.com/VisDrone/VisDrone-Dataset).',
           'Официальные train/val/test-dev; исходная разметка адаптирована к пяти классам транспорта.',
           'Съемка с дрона; результаты не доказывают качество на стационарной камере.', '',
           '## Подготовленные данные','', '| Выборка | Изображений | Рамок транспорта |', '|---|---:|---:|']
    for split,stats in dataset['splits'].items():
        lines.append(f"| {split} | {stats['images']} | {sum(stats['boxes_by_class'].values())} |")
    lines.extend(['',f"Для первого запуска использованы {dataset['pilot']['images']} тренировочных изображений (seed 42); val и test сохранены полностью.",
                  f"Исключено точных дубликатов: {len(dataset['duplicates_excluded'])}.", '', '## Результаты','',
                  '| Эксперимент | Эпох в запуске | Инициализация | Тест precision | Тест recall | Тест mAP50 | Тест mAP50–95 | Время обучения, мин |',
                  '|---|---:|---|---:|---:|---:|---:|---:|'])
    for r in runs:
        m=r['test']
        lines.append(f"| {r['name']} | {r.get('epochs_completed',r['epochs_requested'])} | {r['initialization']} | {m['metrics/precision(B)']:.4f} | {m['metrics/recall(B)']:.4f} | {m['metrics/mAP50(B)']:.4f} | {m['metrics/mAP50-95(B)']:.4f} | {r['training_seconds']/60:.2f} |")
    lines.extend(['']+[f"Веса {r['name']}: `{r['best_weights']}`." for r in runs]+[''])
    if any(r.get('elapsed_time_note') for r in runs):
        lines.extend(['Длительность основного запуска включает длительные перерывы. Это время завершения процесса, а не непрерывная вычислительная производительность; прямое сравнение с pilot некорректно.',''])
    counting=[json.loads(p.read_text()) for p in sorted((ROOT/'reports').glob('counting-*.json'))]
    if counting:
        lines.extend(['## Предварительная проверка подсчета','', '| Модель | Событий | Визуальный ориентир | Совпадений по интервалам | Непокрытых интервалов | Лишних событий |', '|---|---:|---:|---:|---:|---:|'])
        for c in counting:
            t=c['temporal_event_check']
            lines.append(f"| {c['name']} | {c['observed_total']} | {c['reference_total']} | {t['matched_events']} | {len(t['unmatched_reference_events'])} | {len(t['unmatched_predicted_events'])} |")
        lines.extend(['', 'Ориентир размечен ассистентом по контактным листам до просмотра предсказаний и требует подтверждения человеком. Один короткий ролик не определяет общую точность подсчета. Временное сопоставление использует приблизительные интервалы и допуск 6 кадров. У исходной пилотной дообученной модели общий счет 10 совпадает с ориентиром, однако найдено одно непокрытое событие и одно событие вне интервалов; равенство общего счета скрывает компенсацию ошибок. Значения времени обработки записаны в условиях текущего запуска; для сравнения быстродействия нужен отдельный замер при одинаковой нагрузке.', ''])
    lines.extend(['## Границы выводов','',
                  '- Продолжения из local-checkpoint включают предыдущее обучение весов; число эпох в таблице относится только к текущему запуску.',
                  '- Результаты аугментации и одинакового бюджета описаны отдельно в reports/AUGMENTATION_RESULTS.md. Полный расширенный запуск не отделяет эффект дополнительных эпох от аугментации.',
                  '- Pilot использует 1024 изображения; full использует весь train. Разные данные и размеры входа не позволяют приписать изменение качества только инициализации.',
                  '- Оценка YOLO не маскирует исходные игнорируемые области и не является официальным баллом VisDrone.',
                  '- Один seed не дает оценку вариативности обучения; некоторые операции MPS недетерминированы.',
                  '- Precision/recall приведены по библиотечному протоколу оценки, а не при фиксированном пороге интерфейса 0.3.',
                  '- При нулевой полноте высокая precision отдельных редких классов не подтверждает полезное обнаружение.',
                  '- Оценка обнаружения не заменяет проверку точности подсчета по вручную размеченным видео.',
                  '- Порог интерфейса не использовался для подбора тестовых результатов.','',
                  '## Воспроизведение','',
                  'Команды, параметры, результаты по классам и версии сохранены в README, reports/vehicle-*.json и runs/experiments/*/args.yaml.'])
    (ROOT/'reports/EXPERIMENT_REPORT.md').write_text('\n'.join(lines)+'\n')
    if runs:
        fig,ax=plt.subplots(figsize=(max(8,len(runs)*1.8),5.5))
        x=list(range(len(runs)))
        ax.bar([i-.18 for i in x],[r['test']['metrics/mAP50(B)'] for r in runs],width=.36,label='mAP@0.50')
        ax.bar([i+.18 for i in x],[r['test']['metrics/mAP50-95(B)'] for r in runs],width=.36,label='mAP@0.50:0.95')
        ax.set_xticks(x,[r['name'].replace('vehicle-','').replace('-','\n') for r in runs])
        ax.set_ylim(0,1)
        ax.set_ylabel('Average precision')
        ax.set_title('VisDrone vehicle subset: held-out test evaluation')
        for bars in ax.containers:
            ax.bar_label(bars,fmt='%.3f',padding=3,fontsize=9)
        ax.legend()
        ax.spines[['top','right']].set_visible(False)
        fig.tight_layout()
        fig.savefig(ROOT/'reports/model-comparison.png',dpi=200)
        plt.close(fig)
        recommended = max(runs,key=lambda r:r['validation']['metrics/mAP50-95(B)'])
        (ROOT/'reports/recommended-model.json').write_text(json.dumps({'name':recommended['name'],'weights':recommended['best_weights'],'inference_imgsz':recommended.get('recommended_inference_imgsz',recommended['imgsz']),'selection':'Highest validation mAP50-95 among completed experiments; test metrics are not used for selection.'},indent=2))

if __name__=='__main__':
    main()
