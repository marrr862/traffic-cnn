"""Plot matched augmentation results without conflating mAP with counting accuracy."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    comparison=json.loads((ROOT/'reports/augmentation-comparison.json').read_text())
    names=['vehicle-finetune-full','vehicle-augmentation-control','vehicle-augmentation-expanded']
    if (ROOT/'reports/vehicle-expanded-full.json').exists():
        names.append('vehicle-expanded-full')
    reports=[json.loads((ROOT/f'reports/{name}.json').read_text()) for name in names]
    selected=max(reports,key=lambda r:r['validation']['metrics/mAP50-95(B)'])
    comparison['selected_by_validation']=selected['name']
    if len(reports)>3:
        comparison['runs'][reports[-1]['name']]={s:reports[-1][s] for s in ['validation','test']}
        comparison['full_expansion_protocol']='Additional 3-epoch continuation from the original full checkpoint on all 6469 originals plus 1024 variants. No matched full-data continuation control: its improvement cannot be attributed solely to augmentation.'
    (ROOT/'reports/augmentation-comparison.json').write_text(json.dumps(comparison,indent=2))
    rows=['| Модель | Val mAP50 | Val mAP50-95 | Test mAP50 | Test mAP50-95 |','|---|---:|---:|---:|---:|']
    for r in reports:
        rows.append('| '+r['name']+' | '+' | '.join(f"{r[s][k]*100:.2f}%" for s,k in [('validation','metrics/mAP50(B)'),('validation','metrics/mAP50-95(B)'),('test','metrics/mAP50(B)'),('test','metrics/mAP50-95(B)')])+' |')
    delta=comparison['validation_delta_expanded_minus_control']*100
    text='# Измеренное сравнение аугментации\n\n'+'\n'.join(rows)+f'\n\nРазница expanded − control на validation mAP50-95: {delta:+.2f} процентного пункта. Выбрана по validation: **{comparison["selected_by_validation"]}**.\n\n'+'Контроль и вариант с аугментацией: по 3 эпохи из одного исходного checkpoint, по 2048 примеров за эпоху, 640 px, batch 8, AdamW lr0=0.0001, seed 42. Новых независимых сцен нет. Встроенные преобразования YOLO одинаковы. Test-dev уже использовался ранее и не является новой слепой проверкой.'+'\n\nТри эпохи на подвыборке — короткое исследование, один seed; причинный эффект и надежность на новых камерах не установлены. У исходной основной модели другой предыдущий бюджет обучения. Только control и expanded имеют одинаковый бюджет дополнительного обучения.\n'
    if len(reports)>3:
        text+='\nДополнительный full-expanded запуск: 3 эпохи на всех 7493 тренировочных файлах, старт из исходного full checkpoint. Для него нет контрольного продолжения на полном неизмененном наборе; эффект большего обучения и эффект аугментации не отделены.\n'
    (ROOT/'reports/AUGMENTATION_RESULTS.md').write_text(text)
    categories=['car','van','truck','bus','motorcycle']
    fig,axes=plt.subplots(1,2,figsize=(13,4.5))
    labels=['Исходная модель','Подвыборка: контроль','Подвыборка: аугментация','Полный расширенный'][:len(reports)]
    for i,r in enumerate(reports):
        axes[0].bar(i-.15,r['validation']['metrics/mAP50-95(B)']*100,.3,color='#2563eb',label='Проверочная выборка' if i==0 else None)
        axes[0].bar(i+.15,r['test']['metrics/mAP50-95(B)']*100,.3,color='#eab308',label='Тестовая выборка' if i==0 else None)
        axes[1].plot(categories,[r['test_by_class'][c]['mAP50_95']*100 for c in categories],marker='o',label=labels[i])
    axes[0].set_xticks(range(len(reports)),labels,rotation=15);axes[0].legend();axes[0].set_ylabel('mAP50-95 (%)');axes[0].set_title('Одинаковые выборки оценки')
    axes[1].set_title('AP50-95 по классам на test');axes[1].set_ylabel('AP50-95 (%)');axes[1].legend(fontsize=8)
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_ylim(bottom=0)
    fig.tight_layout();fig.savefig(ROOT/'reports/augmentation-comparison.png',dpi=170);plt.close(fig)
    selected=next(r for r in reports if r['name']==comparison['selected_by_validation'])
    (ROOT/'reports/recommended-model.json').write_text(json.dumps(dict(name=selected['name'],weights=selected['best_weights'],inference_imgsz=selected.get('recommended_inference_imgsz',selected['imgsz']),selection='Highest validation mAP50-95 among the baseline and matched augmentation continuation runs; test not used for selection.'),indent=2))
    print(text)


if __name__=='__main__':main()
