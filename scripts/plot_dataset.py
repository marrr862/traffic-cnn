import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT/'reports/dataset.json').read_text())
counts = report['splits']['train']['boxes_by_class']
classes = ['car','van','truck','bus','motorcycle']
fig,ax = plt.subplots(figsize=(7,3.6))
bars = ax.bar(classes,[counts[c] for c in classes],color='#285E8E',width=.65)
ax.bar_label(bars,labels=[f'{counts[c]:,}'.replace(',',' ') for c in classes],padding=3,fontsize=10)
ax.set_ylim(0,165000)
ax.set_title('Рамки транспортных средств в train',fontsize=12)
ax.set_ylabel('Количество рамок',fontsize=10)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{int(v):,}'.replace(',',' ')))
ax.tick_params(labelsize=10)
ax.spines[['top','right']].set_visible(False)
fig.tight_layout()
fig.savefig(ROOT/'reports/class-distribution-full.png',dpi=220)
plt.close(fig)
