"""Follow-up figures (English labels)."""
import csv, json
from collections import defaultdict
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path('/home/geonug/agent/reports/hvq_fn_audit/followup')
FIG = OUT/'figures'; FIG.mkdir(parents=True, exist_ok=True)
preds = list(csv.DictReader(open('/home/geonug/agent/reports/final_performance_minmax/all_predictions.csv')))
import sqlite3
_con=sqlite3.connect('file:/home/geonug/MV/outputs/fusion_agent_validation_20261124_v1/max16_scores/hvq_max16.sqlite?mode=ro',uri=True)
_m={r[0]:r[1] for r in _con.execute('SELECT product_id,hvq_max16_max FROM products')}
_con.close()
for r in preds:
    r['hvq_mean']=float(r['hvq_mean']); r['hvq_max16_max']=float(_m[r['product_id']])
pos=[r for r in preds if r['truth']=='defect']; neg=[r for r in preds if r['truth']!='defect']

# 1 distributions mean vs max16
fig,ax=plt.subplots(1,2,figsize=(12,4))
ax[0].hist([r['hvq_mean'] for r in neg],bins=60,alpha=.6,label='normal',density=True)
ax[0].hist([r['hvq_mean'] for r in pos],bins=60,alpha=.6,label='defect',density=True)
ax[0].set_title('product hvq_mean_max distribution'); ax[0].legend()
ax[1].hist([r['hvq_max16_max'] for r in neg],bins=60,alpha=.6,label='normal',density=True)
ax[1].hist([r['hvq_max16_max'] for r in pos],bins=60,alpha=.6,label='defect',density=True)
ax[1].set_title('product hvq_max16_max distribution'); ax[1].legend()
fig.tight_layout(); fig.savefig(FIG/'score_distribution_mean_vs_max16.png',dpi=110); plt.close(fig)

# 2 ROC & PR
def roc_pr(rows,key):
    order=sorted(rows,key=lambda r:-r[key]); P=sum(r['truth']=='defect' for r in rows); N=len(rows)-P
    tp=fp=0; xs=[0]; ys=[0]; ps=[1]; rs=[0]
    for r in order:
        if r['truth']=='defect': tp+=1
        else: fp+=1
        xs.append(fp/N); ys.append(tp/P); ps.append(tp/(tp+fp) if tp+fp else 1); rs.append(tp/P)
    return xs,ys,rs,ps
fig,ax=plt.subplots(1,2,figsize=(12,5))
for key,lab in (('hvq_mean','mean_max'),('hvq_max16_max','max16_max')):
    x,y,rc,pr=roc_pr(preds,key)
    ax[0].plot(x,y,label=lab); ax[1].plot(rc,pr,label=lab)
ax[0].plot([0,1],[0,1],'k--'); ax[0].set_title('ROC'); ax[0].legend(); ax[0].set_xlabel('FPR'); ax[0].set_ylabel('TPR')
ax[1].set_title('Precision-Recall'); ax[1].legend(); ax[1].set_xlabel('Recall'); ax[1].set_ylabel('Precision')
fig.tight_layout(); fig.savefig(FIG/'roc_pr_mean_vs_max16.png',dpi=110); plt.close(fig)

# 3-4 category AUROC / FNR / FPR (from score_comparison + recompute per cat AUROC for both variants)
import bisect
def auc(rows,key):
    p=[r[key] for r in rows if r['truth']=='defect']; n=sorted(r[key] for r in rows if r['truth']!='defect')
    w=t=0
    for s in p:
        w+=bisect.bisect_left(n,s); t+=bisect.bisect_right(n,s)-bisect.bisect_left(n,s)
    return (w+0.5*t)/(len(p)*len(n)) if p and n else None
by=defaultdict(list)
for r in preds: by[r['category']].append(r)
cats=sorted(by)
fig,ax=plt.subplots(figsize=(11,5))
x=np.arange(len(cats))
ax.bar(x-0.2,[auc(by[c],'hvq_mean') for c in cats],0.4,label='mean_max')
ax.bar(x+0.2,[auc(by[c],'hvq_max16_max') for c in cats],0.4,label='max16_max')
ax.set_xticks(x); ax.set_xticklabels(cats,rotation=60,ha='right',fontsize=7)
ax.set_title('Category AUROC: mean_max vs max16_max'); ax.legend()
fig.tight_layout(); fig.savefig(FIG/'category_auroc.png',dpi=110); plt.close(fig)

# complementarity stacked (test)
comp=json.load(open(OUT/'metric_consistency.json'))['phase2']['test'] if (OUT/'metric_consistency.json').exists() else None
# 5-9 candidate charts from fusion_candidate_comparison.csv
cand=list(csv.DictReader(open(OUT/'fusion_candidate_comparison.csv')))
labels=[c['candidate'] for c in cand]
f1=[float(c['test_b_f1']) for c in cand]
rec=[float(c['test_b_recall']) for c in cand]
fpr=[float(c['test_b_fpr']) for c in cand]
fig,ax=plt.subplots(figsize=(11,5))
xx=np.arange(len(labels))
ax.bar(xx-0.25,f1,0.25,label='F1')
ax.bar(xx,[r for r in rec],0.25,label='Recall')
ax.bar(xx+0.25,fpr,0.25,label='FPR')
ax.set_xticks(xx); ax.set_xticklabels(labels,rotation=45,ha='right',fontsize=7)
ax.set_title('Fusion candidates — Test (hold-included binary)'); ax.legend()
fig.tight_layout(); fig.savefig(FIG/'fusion_candidates.png',dpi=110); plt.close(fig)

# scatter mean vs max16 colored by truth (mapped/subset all products)
fig,ax=plt.subplots(figsize=(6,6))
ax.scatter([r['hvq_mean'] for r in neg],[r['hvq_max16_max'] for r in neg],s=3,alpha=.3,label='normal')
ax.scatter([r['hvq_mean'] for r in pos],[r['hvq_max16_max'] for r in pos],s=3,alpha=.3,label='defect')
ax.set_xlabel('hvq_mean_max'); ax.set_ylabel('hvq_max16_max'); ax.legend(); ax.set_title('Mean vs Max16 product scores')
fig.tight_layout(); fig.savefig(FIG/'mean_vs_max16_scatter.png',dpi=110); plt.close(fig)
print('figures:', sorted(p.name for p in FIG.glob('*.png')))
