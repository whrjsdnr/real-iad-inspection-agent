"""HVQ false-negative audit analysis. Read-only on source data; writes reports/hvq_fn_audit/."""
import csv, io, json, sqlite3, math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('/home/geonug/agent')
OUT = ROOT/'reports/hvq_fn_audit'
BASE = Path('/home/geonug/MV/outputs/fusion_agent_validation_20261124_v1')
con = sqlite3.connect('file:'+str(BASE/'max16_scores/hvq_max16.sqlite')+'?mode=ro', uri=True)
con.row_factory = sqlite3.Row

views = [dict(r) for r in con.execute('SELECT product_id,camera,hvq_mean,hvq_max16,rtdetr_raw FROM views')]
products = [dict(r) for r in con.execute('SELECT product_id,category,split,truth,hvq_mean_max,hvq_max16_max FROM products')]
con.close()
pred_path = ROOT/'reports/final_performance_minmax/all_predictions.csv'
preds = list(csv.DictReader(pred_path.open()))

# ---------- Phase 2: units / labels ----------
per_product = defaultdict(list)
for v in views: per_product[v['product_id']].append(v)
view_counts = Counter(len(v) for v in per_product.values())
cam_ok = all(sorted(x['camera'] for x in vs) == ['C1','C2','C3','C4','C5'] for vs in per_product.values())
dup_pc = len(views) - len({(v['product_id'], v['camera']) for v in views})
truth_by_pid = {p['product_id']: p['truth'] for p in products}
label_flip = sum(1 for p in products if p['truth'] not in ('defect','normal'))
pred_pids = {r['product_id'] for r in preds}
phase2 = {
  'products': len(products), 'views': len(views),
  'views_per_product_distribution': dict(view_counts),
  'all_products_have_exactly_5_views': view_counts == {5: len(products)},
  'camera_set_ok_all_products': cam_ok,
  'duplicate_product_camera_rows': dup_pc,
  'truth_labels': dict(Counter(p['truth'] for p in products)),
  'truth_value_invalid': label_flip,
  'pred_products_match_score_products': pred_pids == set(per_product),
  'note': '제품 단위 정답(truth)만 존재. 시점 단위 결함 가시성 라벨은 없어 시점별 미탐은 산출하지 않음.',
}
(OUT/'phase2_units.json').write_text(json.dumps(phase2, ensure_ascii=False, indent=2))

# ---------- score tables ----------
by_pid = {}
for p in products:
    by_pid[p['product_id']] = dict(p)
    by_pid[p['product_id']]['views'] = per_product[p['product_id']]
for r in preds:
    d = by_pid[r['product_id']]
    d['fusion_score'] = float(r['fusion_score']); d['verdict'] = r['verdict']
    d['rt_raw'] = float(r['rtdetr_raw']); d['hv_mean'] = float(r['hvq_mean'])  # product-level stored aggregates
    d['split'] = r['split']; d['truth'] = r['truth']; d['category'] = r['category']
    d['product_hvq_mean'] = float(r['product_hvq_mean'])

def agg(scores, kind):
    s = sorted(scores, reverse=True)
    if kind == 'mean': return sum(s)/len(s)
    if kind == 'max': return s[0]
    if kind == 'top2': return sum(s[:2])/2
    if kind == 'top3': return sum(s[:3])/3
    if kind == 'median':
        n=len(s); return s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
    raise ValueError(kind)

def metrics(pairs):
    """pairs: list[(score, truth_defect_bool)] -> dict with ROC-AUC via rank"""
    pos = [s for s,t in pairs if t]; neg = [s for s,t in pairs if not t]
    tp=fp=0
    y = [(s,1) for s in pos]+[(s,0) for s in neg]
    order = sorted(y, key=lambda x:-x[0])
    # AUROC via Mann-Whitney
    import itertools
    wins=ties=0
    neg_sorted=sorted(neg)
    import bisect
    for s in pos:
        lo=bisect.bisect_right(neg_sorted, s); lt=bisect.bisect_left(neg_sorted, s)
        wins+=lt; ties+=lo-lt
    denom=len(pos)*len(neg)
    auroc=(wins+0.5*ties)/denom if denom else None
    # best F1 threshold sweep
    best=None
    for th in sorted({s for s,_ in y}, reverse=True):
        tp=sum(1 for s,t in y if s>=th and t); fp=sum(1 for s,t in y if s>=th and not t)
        fn=len(pos)-tp
        prec=tp/(tp+fp) if tp+fp else 0; rec=tp/len(pos) if pos else 0
        f1=2*prec*rec/(prec+rec) if prec+rec else 0
        if best is None or f1>best[0]: best=(f1,th,rec,fn,fp,prec)
    # AP
    ap=0.0; tp=0
    for i,(s,t) in enumerate(order,1):
        if t: tp+=1; ap+=tp/i
    ap/=len(pos) if pos else 1
    return {'n_pos':len(pos),'n_neg':len(neg),'auroc':auroc,'ap':ap,
            'best_f1':best[0],'best_threshold':best[1],'best_recall':best[2],'best_fn':best[3],'best_fp':best[4],'best_precision':best[5]}

# ---------- Phase 4/6: aggregation comparison ----------
kinds=['mean','max','top2','top3','median']
rows=[]
val_pairs_by_kind={k:[] for k in kinds}; test_pairs_by_kind={k:[] for k in kinds}
all_pairs_by_kind={k:[] for k in kinds}
max16_pairs={'val':[], 'test':[], 'all':[]}
for pid,d in by_pid.items():
    scores=[v['hvq_mean'] for v in d['views']]
    truth = d['truth']=='defect'
    for k in kinds:
        s=agg(scores,k)
        all_pairs_by_kind[k].append((s,truth))
        (val_pairs_by_kind[k] if d['split']=='validation' else test_pairs_by_kind[k] if d['split']=='test' else []).append((s,truth)) if d['split'] in ('validation','test') else None
    m=d['hvq_max16_max'] if 'hvq_max16_max' in d else None
    key='val' if d['split']=='validation' else 'test' if d['split']=='test' else None
for pid,d in by_pid.items():
    pass
# rebuild with max16 from products rows
for p in products:
    d=by_pid[p['product_id']]
    m=d.get('hvq_max16_max') or p.get('hvq_max16_max')
# products rows already carry hvq_max16_max
for p in products:
    d=by_pid[p['product_id']]
    d['hvq_max16_max']=p['hvq_max16_max']
    key='val' if p['split']=='validation' else 'test' if p['split']=='test' else None
    if key: max16_pairs[key].append((p['hvq_max16_max'], p['truth']=='defect'))
# fix: append val/test pairs properly for kinds
for pid,d in by_pid.items():
    scores=[v['hvq_mean'] for v in d['views']]
    truth=d['truth']=='defect'
    for k in kinds:
        s=agg(scores,k)
        if d['split']=='validation': val_pairs_by_kind[k].append((s,truth))
        elif d['split']=='test': test_pairs_by_kind[k].append((s,truth))

with (OUT/'hvq_score_aggregation_comparison.csv').open('w',newline='') as f:
    w=csv.writer(f); w.writerow(['score_variant','product_aggregation','fit_split','n_pos','n_neg','auroc','ap','best_f1','best_threshold','best_recall','best_fn','best_fp'])
    for k in kinds:
        mval=metrics(val_pairs_by_kind[k]); mtest=metrics(test_pairs_by_kind[k])
        w.writerow([f'view_hvq_mean_{k}','product_'+k,'validation',mval['n_pos'],mval['n_neg'],mval['auroc'],mval['ap'],mval['best_f1'],mval['best_threshold'],mval['best_recall'],mval['best_fn'],mval['best_fp']])
        w.writerow([f'view_hvq_mean_{k}','product_'+k,'test',mtest['n_pos'],mtest['n_neg'],mtest['auroc'],mtest['ap'],mtest['best_f1'],mtest['best_threshold'],mtest['best_recall'],mtest['best_fn'],mtest['best_fp']])
    mv=metrics(max16_pairs['val']); mt=metrics(max16_pairs['test'])
    w.writerow(['product_hvq_max16_max','stored_max','validation',mv['n_pos'],mv['n_neg'],mv['auroc'],mv['ap'],mv['best_f1'],mv['best_threshold'],mv['best_recall'],mv['best_fn'],mv['best_fp']])
    w.writerow(['product_hvq_max16_max','stored_max','test',mt['n_pos'],mt['n_neg'],mt['auroc'],mt['ap'],mt['best_f1'],mt['best_threshold'],mt['best_recall'],mt['best_fn'],mt['best_fp']])

# current buggy reference: hvq_mean_max >= 81
cur = {'tp':0,'fn':0,'fp':0,'tn':0}
for p in products:
    pos = p['hvq_mean_max'] >= 81.0
    t = p['truth']=='defect'
    if pos and t: cur['tp']+=1
    elif pos and not t: cur['fp']+=1
    elif not pos and t: cur['fn']+=1
    else: cur['tn']+=1

# corrected reference: fit global threshold on validation (max F1) for view_hvq_mean max aggregation
fit = metrics(val_pairs_by_kind['max'])
TH = fit['best_threshold']
conf={'tp':0,'fn':0,'fp':0,'tn':0}
for p in products:
    pos = p['hvq_mean_max'] >= TH
    t = p['truth']=='defect'
    if pos and t: conf['tp']+=1
    elif pos and not t: conf['fp']+=1
    elif not pos and t: conf['fn']+=1
    else: conf['tn']+=1

def rates(c):
    tp,fn,fp,tn=c['tp'],c['fn'],c['fp'],c['tn']
    rec=tp/(tp+fn) if tp+fn else None
    return {'recall':rec,'fnr':1-rec if rec is not None else None,'fpr':fp/(fp+tn) if fp+tn else None,
            'precision':tp/(tp+fp) if tp+fp else None,
            'f1':2*tp/(2*tp+fp+fn) if (tp+fp+fn) else None,
            'specificity':tn/(tn+fp) if tn+fp else None}
with (OUT/'hvq_confusion_matrix.csv').open('w',newline='') as f:
    w=csv.writer(f); w.writerow(['variant','scope','threshold_source','threshold','tp','fn','fp','tn','recall','fnr','fpr','precision','f1','specificity','note'])
    for scope,c in (('all_24000',cur),('test_3593',None)):
        if c:
            r=rates(c); w.writerow(['hvq_mean_max>=81 (current reference)',scope,'fusion.json hvq.threshold_default (max16-scale)',81.0,c['tp'],c['fn'],c['fp'],c['tn'],r['recall'],r['fnr'],r['fpr'],r['precision'],r['f1'],r['specificity'],'max16 시대 임계값을 heatmap_mean 척도에 적용해 전수 정상 판정'])
    ctest={'tp':0,'fn':0,'fp':0,'tn':0}
    for p in products:
        if p['split']!='test': continue
        pos=p['hvq_mean_max']>=TH; t=p['truth']=='defect'
        if pos and t: ctest['tp']+=1
        elif pos and not t: ctest['fp']+=1
        elif not pos and t: ctest['fn']+=1
        else: ctest['tn']+=1
    r=rates(conf); w.writerow(['hvq_mean_max>=Val-fitted TH (corrected reference)','all_24000','validation split, max-F1 threshold',TH,conf['tp'],conf['fn'],conf['fp'],conf['tn'],r['recall'],r['fnr'],r['fpr'],r['precision'],r['f1'],r['specificity'],'참고 지표. 운영 퓨전 규칙과 무관'])
    r=rates(ctest); w.writerow(['hvq_mean_max>=Val-fitted TH (corrected reference)','test_3593','validation split, max-F1 threshold (test 고정 적용)',TH,ctest['tp'],ctest['fn'],ctest['fp'],ctest['tn'],r['recall'],r['fnr'],r['fpr'],r['precision'],r['f1'],r['specificity'],''])

# ---------- Phase 5: threshold sweep ----------
with (OUT/'hvq_threshold_sweep.csv').open('w',newline='') as f:
    w=csv.writer(f); w.writerow(['split','threshold','tp','fn','fp','tn','recall','fnr','fpr','precision','f1'])
    for name,pairs in (('validation',val_pairs_by_kind['max']),('test',test_pairs_by_kind['max'])):
        for th in sorted({s for s,_ in pairs}, reverse=True)[::max(1,len({s for s,_ in pairs})//200)]:
            c={'tp':0,'fn':0,'fp':0,'tn':0}
            for s,t in pairs:
                pos=s>=th
                if pos and t:c['tp']+=1
                elif pos:c['fp']+=1
                elif t:c['fn']+=1
                else:c['tn']+=1
            r=rates(c); w.writerow([name,th,c['tp'],c['fn'],c['fp'],c['tn'],r['recall'],r['fnr'],r['fpr'],r['precision'],r['f1']])

# ---------- Phase 7: per category ----------
with (OUT/'hvq_category_metrics.csv').open('w',newline='') as f:
    w=csv.writer(f); w.writerow(['category','n','n_defect','tp','fn','fp','tn','recall','fnr','fpr','f1','hvq_mean_max_auroc','hvq_mean_max_ap','threshold_used'])
    cats=defaultdict(list)
    for p in products: cats[p['category']].append(p)
    for cat in sorted(cats):
        ps=cats[cat]
        c={'tp':0,'fn':0,'fp':0,'tn':0}
        for p in ps:
            pos=p['hvq_mean_max']>=TH; t=p['truth']=='defect'
            if pos and t:c['tp']+=1
            elif pos and not t:c['fp']+=1
            elif not pos and t:c['fn']+=1
            else:c['tn']+=1
        r=rates(c)
        m=metrics([(p['hvq_mean_max'],p['truth']=='defect') for p in ps])
        w.writerow([cat,len(ps),sum(1 for p in ps if p['truth']=='defect'),c['tp'],c['fn'],c['fp'],c['tn'],r['recall'],r['fnr'],r['fpr'],r['f1'],m['auroc'],m['ap'],TH])

# defect type metrics
with (OUT/'hvq_defect_type_metrics.csv').open('w',newline='') as f:
    w=csv.writer(f); w.writerow(['defect_type','n_defect_products','tp','fn','recall','fnr'])
    types=defaultdict(lambda:{'tp':0,'fn':0})
    for p in products:
        if p['truth']!='defect': continue
        parts=p['product_id'].split('/')
        dt=parts[1] if len(parts)>2 else 'unknown'
        pos=p['hvq_mean_max']>=TH
        types[dt]['tp' if pos else 'fn']+=1
    for dt in sorted(types):
        t=types[dt]; rec=t['tp']/(t['tp']+t['fn']) if t['tp']+t['fn'] else None
        w.writerow([dt,t['tp']+t['fn'],t['tp'],t['fn'],rec,1-rec if rec is not None else None])

# ---------- Phase 8: complementarity ----------
groups=Counter(); by_cat=defaultdict(Counter)
for p in products:
    rt = p['hvq_mean_max'] is not None
for p in products:
    rt_pos = any(v['rtdetr_raw']>=0.4 for v in per_product[p['product_id']])
    hv_pos = p['hvq_mean_max']>=TH
    t=p['truth']=='defect'
    if t:
        g='A_both' if (rt_pos and hv_pos) else 'B_rt_only' if rt_pos else 'C_hvq_only' if hv_pos else 'D_neither'
    else:
        g='N_both_fp' if (rt_pos and hv_pos) else 'N_rt_only' if rt_pos else 'N_hvq_only' if hv_pos else 'N_none'
    groups[g]+=1; by_cat[p['category']][g]+=1
with (OUT/'model_complementarity.csv').open('w',newline='') as f:
    w=csv.writer(f); w.writerow(['group','definition','products','share_of_group_base'])
    defect_total=sum(v for k,v in groups.items() if k[0] in 'ABCD')
    normal_total=sum(v for k,v in groups.items() if k[0]=='N')
    for g in ('A_both','B_rt_only','C_hvq_only','D_neither'):
        w.writerow([g,'defect products',groups[g],groups[g]/defect_total if defect_total else None])
    for g in ('N_both_fp','N_rt_only','N_hvq_only','N_none'):
        w.writerow([g,'normal products',groups[g],groups[g]/normal_total if normal_total else None])
    w.writerow([])
    w.writerow(['category']+list(groups.keys()))
    for cat in sorted(by_cat):
        w.writerow([cat]+[by_cat[cat][g] for g in groups.keys()])

# ---------- Phase 9: FN cases ----------
with (OUT/'hvq_false_negative_cases.csv').open('w',newline='') as f:
    w=csv.writer(f); w.writerow(['product_id','category','split','hvq_mean_max','hvq_max16_max','rt_caught','fusion_verdict','has_stored_map'])
    maps = {m.name for m in (BASE/'max16_scores/hvq_max16.sqlite').parent.glob('maps/*')} if (BASE/'max16_scores/hvq_max16.sqlite').parent.joinpath('maps').exists() else set()
    map_idx = set()
    for m in maps:
        map_idx.add(m.split('.')[0])
    for p in products:
        if p['truth']=='defect' and not (p['hvq_mean_max']>=TH):
            rt_pos = any(v['rtdetr_raw']>=0.4 for v in per_product[p['product_id']])
            w.writerow([p['product_id'],p['category'],p['split'],p['hvq_mean_max'],p['hvq_max16_max'],rt_pos,by_pid[p['product_id']]['verdict'],p['product_id'] in map_idx])

summary={'corrected_threshold':TH,'current_reference':cur,'corrected_reference_all':conf,'corrected_reference_test':ctest,
         'complementarity':dict(groups)}
(OUT/'analysis_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps({'th':TH,'current':cur,'corrected_all':conf,'corrected_test':ctest,'groups':dict(groups)},ensure_ascii=False))
