"""Present inference-size results separately from training-data changes."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]


def main():
    report=json.loads((ROOT/'reports/resolution-comparison.json').read_text())
    rows=['# Сравнение размера входа CNN','',f"Один checkpoint: {report['name']}. Размер выбран по validation: {report['selected_imgsz_by_validation']} px.",'','| Вход | Val mAP50 | Val mAP50-95 | Test mAP50 | Test mAP50-95 |','|---|---:|---:|---:|---:|']
    sizes=sorted(report['sizes'],key=int)
    for size in sizes:
        r=report['sizes'][size]
        rows.append('| '+size+' | '+' | '.join(f"{r[s]['metrics'][k]*100:.2f}%" for s,k in [('validation','metrics/mAP50(B)'),('validation','metrics/mAP50-95(B)'),('test','metrics/mAP50(B)'),('test','metrics/mAP50-95(B)')])+' |')
    rows+=['','Изменение размера не является добавлением данных или новым обучением. Test-dev уже применялся в других экспериментах; результаты описательные. Замеры скорости библиотеки не заменяют измерение FPS дорожного видео при одинаковых условиях. Для оценки подсчета нужны отдельно размеченные события.']
    (ROOT/'reports/RESOLUTION_RESULTS.md').write_text('\n'.join(rows)+'\n')
    fig,ax=plt.subplots(figsize=(8,4))
    for i,size in enumerate(sizes):
        value=report['sizes'][size]
        for offset,split,color in [(-.18,'validation','#2563eb'),(.18,'test','#f59e0b')]:
            bar=ax.bar(i+offset,value[split]['metrics']['metrics/mAP50-95(B)']*100,.36,color=color,label=split if i==0 else None)
            ax.bar_label(bar,fmt='%.2f%%',padding=3)
    ax.set_xticks(range(len(sizes)),[s+' px' for s in sizes]);ax.set_ylabel('mAP50-95 (%)');ax.set_ylim(0,max(report['sizes'][s][split]['metrics']['metrics/mAP50-95(B)']*100 for s in sizes for split in ['validation','test'])*1.18);ax.set_title('Одна модель, одинаковые выборки');ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(ROOT/'reports/resolution-comparison.png',dpi=170);plt.close(fig)
    print('\n'.join(rows))


if __name__=='__main__':main()
