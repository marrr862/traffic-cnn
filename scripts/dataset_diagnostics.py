"""Describe class imbalance and vehicle sizes after a 640-pixel resize."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
NAMES=['car','van','truck','bus','motorcycle']


def main():
    data=ROOT/'data/visdrone-vehicles';report={}
    for split in ['train','val','test']:
        sizes={name:[] for name in NAMES}
        for image in sorted((data/'images'/split).glob('*.jpg')):
            with Image.open(image) as opened:width,height=opened.size
            scale=640/max(width,height)
            for row in (data/'labels'/split/image.with_suffix('.txt').name).read_text().splitlines():
                category,x,y,w,h=map(float,row.split())
                sizes[NAMES[int(category)]].append(min(w*width,h*height)*scale)
        report[split]={name:dict(boxes=len(values),median_min_side_at_640=float(np.median(values)),fraction_min_side_below_10px=float(np.mean(np.array(values)<10))) for name,values in sizes.items()}
    result=dict(protocol='Original corpus only. Minimum box side after proportional resize to maximum side 640; excludes online geometric augmentations. This is a descriptive statistic, not a measured cause of model errors.',splits=report)
    (ROOT/'reports/dataset-diagnostics.json').write_text(json.dumps(result,indent=2))
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    axes[0].bar(NAMES,[report['train'][n]['boxes'] for n in NAMES]);axes[0].set_title('Число рамок в исходном train');axes[0].set_ylabel('Размеченных объектов')
    axes[1].bar(NAMES,[report['test'][n]['fraction_min_side_below_10px']*100 for n in NAMES],color='#f59e0b');axes[1].set_title('Минимальная сторона <10 px при входе 640');axes[1].set_ylabel('Доля объектов test (%)');axes[1].set_ylim(0,100)
    for ax in axes:ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(ROOT/'reports/dataset-diagnostics.png',dpi=170);plt.close(fig)
    print(json.dumps(report['test'],indent=2))


if __name__=='__main__':main()
