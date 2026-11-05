"""Armenian figures for the thesis: pipeline diagram and model comparison chart.

Usage: python scripts/thesis_figures_hy.py   (writes reports/thesis/pipeline-hy.png and models-hy.png)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/thesis'
for candidate in [Path.home() / 'Library/Fonts/sylfaen.ttf', Path('C:/Windows/Fonts/sylfaen.ttf')]:
    if candidate.exists():
        font_manager.fontManager.addfont(str(candidate))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(candidate)).get_name()
        break


def pipeline():
    steps = [
        ('Տեսանյութ\nկամ ուղիղ հոսք', '#E7EDF2'),
        ('CNN հայտնաբերում\nYOLOv8 (սալիկներ՝\nըստ ցանկության)', '#D6E6F5'),
        ('Հետագծում\nByteTrack (ID)', '#D6E6F5'),
        ('Հաշվման գծեր\nհիստերեզիս,\nկրկնակի ID-ի զտիչ', '#FCE8D2'),
        ('Ամփոփում\nq, v, k, LOS, q = k·v,\nհավաստիություն', '#FCE8D2'),
        ('Արտահանում\nMP4, CSV, JSON,\nմիջերես', '#E7EDF2'),
    ]
    fig, ax = plt.subplots(figsize=(13, 4.6))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 4.6)
    ax.axis('off')
    width, gap = 1.85, 0.32
    for i, (text, color) in enumerate(steps):
        x = 0.15 + i * (width + gap)
        ax.add_patch(FancyBboxPatch((x, 2.3), width, 1.6, boxstyle='round,pad=0.04', fc=color, ec='#4A5568', lw=1.2))
        ax.text(x + width / 2, 3.1, text, ha='center', va='center', fontsize=9.8)
        if i < len(steps) - 1:
            ax.annotate('', xy=(x + width + gap - 0.02, 3.1), xytext=(x + width + 0.02, 3.1),
                        arrowprops=dict(arrowstyle='->', lw=1.6, color='#2D3748'))
    # calibration branch
    cx = 0.15 + 3 * (width + gap)
    ax.add_patch(FancyBboxPatch((cx - 1.1, 0.35), 2.9, 1.25, boxstyle='round,pad=0.04', fc='#E2F0D9', ec='#4A5568', lw=1.2))
    ax.text(cx + 0.35, 0.97, 'Տրամաչափում\n(4 կետ, հոմոգրաֆիա)՝ մետրեր,\nարագություն, խտություն', ha='center', va='center', fontsize=10)
    ax.annotate('', xy=(cx + 0.35, 2.28), xytext=(cx + 0.35, 1.65), arrowprops=dict(arrowstyle='->', lw=1.6, color='#2D3748'))
    tx = 0.15 + 1 * (width + gap)
    ax.add_patch(FancyBboxPatch((tx - 0.6, 0.35), 2.9, 1.25, boxstyle='round,pad=0.04', fc='#EDE7F6', ec='#4A5568', lw=1.2))
    ax.text(tx + 0.85, 0.97, 'Ուսուցանված կշիռներ\nVisDrone + MIO-TCD,\nYOLOv8n / YOLOv8s', ha='center', va='center', fontsize=10)
    ax.annotate('', xy=(tx + 0.85, 2.28), xytext=(tx + 0.85, 1.65), arrowprops=dict(arrowstyle='->', lw=1.6, color='#2D3748'))
    fig.savefig(OUT / 'pipeline-hy.png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def models():
    data = json.loads((ROOT / 'reports/road-model-comparison.json').read_text())
    names = {'vehicle-hires-960': 'vehicle-hires-960\n(YOLOv8n, VisDrone)',
             'vehicle-road-combined': 'vehicle-road-combined\n(YOLOv8n, VisDrone + MIO-TCD)',
             'vehicle-road-yolov8s': 'vehicle-road-yolov8s\n(YOLOv8s, VisDrone + MIO-TCD)'}
    groups = [('visdrone@960', 'VisDrone թեստ, 960 պքս'), ('mio-tcd@640', 'MIO-TCD թեստ, 640 պքս')]
    colors = ['#9FB3C8', '#5B8DB8', '#1F4E79']
    fig, ax = plt.subplots(figsize=(10, 4.8))
    bar = 0.26
    for j, (model, label) in enumerate(names.items()):
        values = [data[model][key]['metrics/mAP50(B)'] * 100 for key, _ in groups]
        xs = [i + (j - 1) * bar for i in range(len(groups))]
        bars = ax.bar(xs, values, bar, label=label, color=colors[j])
        for x, v in zip(xs, values):
            ax.text(x, v + 1.2, f'{v:.1f}'.replace('.', ','), ha='center', fontsize=10)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([g[1] for g in groups], fontsize=11)
    ax.set_ylabel('mAP50, %', fontsize=11)
    ax.set_ylim(0, 100)
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(fontsize=9.5, frameon=False, loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    fig.savefig(OUT / 'models-hy.png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    pipeline()
    models()
    print('Saved pipeline-hy.png, models-hy.png')
