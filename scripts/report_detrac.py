"""Summarize completed external checks without pooling detection AP across cameras."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    checks=[json.loads(p.read_text()) for p in sorted((ROOT/'reports').glob('detrac-comparison-MVI_*.json'))]
    rows=[]
    for check in checks:
        for result in check['results']:
            c,d=result['counting'],result['detection']
            rows.append(dict(sequence=check['reference']['sequence'],frames=check['reference']['frames'],model=result['name'],imgsz=result['imgsz'],reference=c['reference_total'],predicted=c['predicted_total'],matched=c['matched_events'],missed=c['missed_events'],extra=c['extra_events'],event_f1=c['event_f1'],vehicle_AP50=d['vehicle_AP50'],vehicle_AP50_95=d['vehicle_AP50_95'],processing_fps=c['processing_fps']))
    aggregate=[]
    for model in sorted({row['model'] for row in rows}):
        selected=[r for r in rows if r['model']==model]
        matched=sum(r['matched'] for r in selected);truth=sum(r['reference'] for r in selected);pred=sum(r['predicted'] for r in selected)
        aggregate.append(dict(model=model,sequences=len(selected),reference=truth,predicted=pred,matched=matched,missed=truth-matched,extra=pred-matched,event_precision=matched/pred if pred else None,event_recall=matched/truth if truth else None,event_f1=2*matched/(truth+pred) if truth+pred else None))
    report=dict(rows=rows,counting_aggregate=aggregate,selection='Planned first 300 frames of first three alphabetic test sequences; only MVI_39031 completed before author Drive quota blocked further downloads; no selection by model score',download_limitation='Google Drive Quota exceeded for further scenes',training_on_detrac=False,limitations='Small external transfer check, correlated frames; custom class-agnostic detection AP, not official UA-DETRAC protocol or five-class VisDrone mAP. Events derived from published trajectories, not separately human-verified. Models and input sizes selected previously on VisDrone validation. Different checkpoint and input size confound attribution. Counting includes all annotated trajectories; unannotated ignored regions may cause extras.')
    (ROOT/'reports/detrac-external-comparison.json').write_text(json.dumps(report,indent=2))
    text='# Проверка на внешнем датасете UA-DETRAC\n\n'
    text+='Источник: [страница автора и архивы](https://sites.google.com/view/daweidu/projects/ua-detrac). Использованы опубликованные тестовые XML с ID транспорта и исходные кадры. Обучение на этих данных не проводилось.\n\n'
    text+='| Видео | Модель / вход | Эталон | Найдено | Пропуски | Лишние | F1 событий | AP50 транспорта | AP50–95 транспорта |\n|---|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for r in rows:
        f1='—' if r['event_f1'] is None else f"{100*r['event_f1']:.2f}%"
        text+=f"| {r['sequence']} ({r['frames']} кадров) | {r['model']} / {r['imgsz']} | {r['reference']} | {r['predicted']} | {r['missed']} | {r['extra']} | {f1} | {100*r['vehicle_AP50']:.2f}% | {100*r['vehicle_AP50_95']:.2f}% |\n"
    text+='\nЗапланированы первые 300 кадров первых трёх последовательностей test по имени до оценки новых сцен. Завершена только MVI_39031: последующие загрузки авторского архива Google Drive заблокированы сообщением Quota exceeded. Каждый фрагмент длится 12 секунд при 25 FPS. Линия заранее фиксирована на 60% высоты. Точка транспорта — нижняя середина рамки; гистерезис 4 px, разрыв до 30 кадров, одно событие на опубликованный ID. Сопоставление событий: направление и интервал кадров, допуск 6 кадров.\n\n'
    text+='AP вычислен для одного объединённого понятия «транспорт», без оценки правильности класса. Категория others сохранена в эталоне; она не переименована в truck. Для детекции исключены рамки, центры которых находятся в опубликованных ignored regions. AP использует IoU 0.50–0.95 и интерполяцию precision по 101 уровню recall. Это собственный протокол, не официальный рейтинг UA-DETRAC. Разметка пересечений автоматически получена из независимых опубликованных траекторий, но отдельно человеком не проверялась.\n\n'
    text+='Высокие значения на небольшом фрагменте не означают такую же точность на всех дорожных камерах. Соседние кадры зависимы. Нельзя непосредственно сравнивать эти AP с пятикомпонентным mAP VisDrone. Сравнение одновременно меняет обученный checkpoint и размер входа; вклад аугментации отдельно не установлен. При подсчёте ignored regions не маскируются, что может создавать дополнительные события. Проверку нужно расширять по камерам и погоде.\n\n'
    text+='Воспроизведение: `python scripts/download_detrac.py --sequence MVI_39031`, затем `python scripts/evaluate_detrac.py --sequence MVI_39031 --device mps` (на другом компьютере можно `cpu`). Для остальных сцен заменить имя на MVI_39051/MVI_39211. Сводка: `python scripts/report_detrac.py`.\n'
    (ROOT/'reports/DETRAC_RESULTS.md').write_text(text)
    print(json.dumps(aggregate,indent=2))
if __name__=='__main__': main()
