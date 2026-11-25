"""Generate audit figures (English labels to avoid CJK font issues in headless env)."""
import csv, json
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path('/home/geonug/agent/reports/hvq_fn_audit')
FIG=OUT/'figures'; FIG.mkdir(exist_ok=True)
import sqlite3
con=sqlite3.connect('file:/home/geonug/MV/outputs/fusion_agent_validation_20261124_v1/max16_scores/hvq_max16.sqlite?mode=ro',uri=True)
con.row_factory=sqlite3.Row
products=[dict(r) for r in con.execute('SELECT product_id,category,split,truth,hvq_mean_max,hvq_max16_max FROM products')]
con.close()
TH=36.02463150024414

pos=[p['hvq_mean_max'] for p in products if p['truth']=='defect']
neg=[p['hvq_mean_max'] for p in products if p['truth']!='defect']
pos16=[p['hvq_max16_max'] for p in products if p['truth']=='defect']
neg16=[p['hvq_max16_max'] for p in products if p['truth']!='defect']

# 1 score distributions
fig,ax=plt.subplots(1,2,figsize=(12,4))
ax[0].hist(neg,bins=80,alpha=.6,label='normal',density=True)
ax[0].hist(pos,bins=80,alpha=.6,label='defect',density=True)
ax[0].axvline(TH,color='r',ls='--',label=f'Val-fitted TH={TH:.2f}')
ax[0].axvline(81.0,color='k',ls=':',label='reported TH=81 (max16 scale)')
ax[0].set_title('product hvq_mean_max distribution'); ax[0].legend()
ax[1].hist(neg16,bins=80,alpha=.6,label='normal',density=True)
ax[1].hist(pos16,bins=80,alpha=.6,label='defect',density=True)
ax[1].axvline(81.0,color='k',ls=':',label='TH=81')
ax[1].set_title('product hvq_max16_max distribution (100-product map subset)' if len(pos16)<12408 else 'product hvq_max16_max')
ax[1].legend()
fig.tight_layout(); fig.savefig(FIG/'score_distributions.png',dpi=110); plt.close(fig)

# 2 ROC curves (approx via sklearn-less computation)
def roc(pairs):
    order=sorted(pairs,key=lambda x:-x[0]); P=sum(t for _,t in pairs); N=len(pairs)-P
    tp=fp=0; xs=[0]; ys=[0]
    for s,t in order:
        if t: tp+=1
        else: fp+=1
        xs.append(fp/N); ys.append(tp/P)
    return xs,ys
val=[(p['hvq_mean_max'],p['truth']=='defect') for p in products if p['split']=='validation']
test=[(p['hvq_mean_max'],p['truth']=='defect') for p in products if p['split']=='test']
fig,ax=plt.subplots(figsize=(5,5))
for name,pairs in (('validation',val),('test',test)):
    x,y=roc(pairs); ax.plot(x,y,label=name)
ax.plot([0,1],[0,1],'k--'); ax.set_xlabel('FPR'); ax.set_ylabel('TPR'); ax.set_title('HVQ mean_max ROC'); ax.legend()
fig.tight_layout(); fig.savefig(FIG/'roc.png',dpi=110); plt.close(fig)

# 3 threshold sweep
sw=list(csv.DictReader((OUT/'hvq_threshold_sweep.csv').open()))
fig,ax=plt.subplots(1,2,figsize=(12,4))
for name,c,ls in (('validation','b','-'),('test','g','-')):
    rows=[r for r in sw if r['split']==name]
    th=[float(r['threshold']) for r in rows]
    ax[0].plot(th,[float(r['recall']) for r in rows],color=c,ls=ls,label=f'{name} recall')
    ax[0].plot(th,[float(r['fpr']) for r in rows],color=c,ls=':',label=f'{name} fpr')
    ax[1].plot(th,[float(r['f1']) for r in rows],color=c,label=f'{name} f1')
ax[0].axvline(TH,color='r',ls='--',label='Val-fitted TH'); ax[1].axvline(TH,color='r',ls='--')
ax[0].set_title('Threshold vs Recall/FPR'); ax[1].set_title('Threshold vs F1')
for a in ax: a.legend(); a.set_xlabel('hvq_mean_max threshold')
fig.tight_layout(); fig.savefig(FIG/'threshold_sweep.png',dpi=110); plt.close(fig)

# 4 category FNR
cats=list(csv.DictReader((OUT/'hvq_category_metrics.csv').open()))
cats=[c for c in cats if c['fnr'] not in ('','None')]
cats.sort(key=lambda c:float(c['fnr']))
fig,ax=plt.subplots(figsize=(9,5))
ax.barh([c['category'] for c in cats],[float(c['fnr']) for c in cats])
ax.set_xlabel('FNR (corrected reference)'); ax.set_title('Category FNR — HVQ standalone (Val-fitted TH)')
fig.tight_layout(); fig.savefig(FIG/'category_fnr.png',dpi=110); plt.close(fig)

# 5 confusion matrix visual (current vs corrected)
import numpy as np
fig,ax=plt.subplots(1,2,figsize=(10,4))
for a,(title,m) in zip(ax,(('current TH=81 (scale error)',{'tp':0,'fn':12408,'fp':0,'tn':11592}),('corrected Val-fitted TH',{'tp':11795,'fn':613,'fp':9195,'tn':2397}))):
    M=np.array([[m['tp'],m['fn']],[m['fp'],m['tn']]])
    a.imshow(M,cmap='Blues'); a.set_title(title)
    a.set_xticks([0,1]); a.set_xticklabels(['pred defect','pred normal'])
    a.set_yticks([0,1]); a.set_yticklabels(['actual defect','actual normal'])
    for i in range(2):
        for j in range(2): a.text(j,i,str(M[i,j]),ha='center',va='center')
fig.tight_layout(); fig.savefig(FIG/'confusion_matrix.png',dpi=110); plt.close(fig)
print('figures done:', sorted(p.name for p in FIG.glob('*.png')))
