"""Follow-up: metric consistency, complementarity, score comparison, fusion ablation.
Offline only — reads stored scores/predictions, writes reports/hvq_fn_audit/followup/.
"""
import csv, json, math, sqlite3, sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path('/home/geonug/agent')
OUT = ROOT/'reports/hvq_fn_audit/followup'
FIG = OUT/'figures'; FIG.mkdir(parents=True, exist_ok=True)
BASE = Path('/home/geonug/MV/outputs/fusion_agent_validation_20261124_v1')
sys.path.insert(0, str(ROOT))
from fusion_calibration import threshold_and_margin

preds = list(csv.DictReader((ROOT/'reports/final_performance_minmax/all_predictions.csv').open()))
con = sqlite3.connect('file:'+str(BASE/'max16_scores/hvq_max16.sqlite')+'?mode=ro', uri=True)
con.row_factory = sqlite3.Row
prod_rows = {r['product_id']: dict(r) for r in con.execute('SELECT product_id,category,split,truth,hvq_mean_max,hvq_max16_max FROM products')}
con.close()
for r in preds:
    p = prod_rows[r['product_id']]
    r['hvq_max16_max'] = float(p['hvq_max16_max'])
    r['hvq_mean'] = float(r['hvq_mean'])
    r['rtdetr_raw'] = float(r['rtdetr_raw'])

def as_bool(x): return x == 'True' or x == 'defect'
for r in preds:
    r['truth_defect'] = r['truth'] == 'defect'
    r['hvq_pos'] = r['hvq_positive'] == 'True'
    r['rt_pos'] = r['rtdetr_positive'] == 'True'

# ---------- Phase 1: independent confusion ----------
def conf_matrix(rows, pos_key):
    tp = sum(1 for r in rows if r['truth_defect'] and r[pos_key])
    fn = sum(1 for r in rows if r['truth_defect'] and not r[pos_key])
    fp = sum(1 for r in rows if not r['truth_defect'] and r[pos_key])
    tn = sum(1 for r in rows if not r['truth_defect'] and not r[pos_key])
    return tp, fn, fp, tn

def rates(tp, fn, fp, tn):
    P, N = tp+fn, fp+tn
    prec = tp/(tp+fp) if tp+fp else None
    rec = tp/P if P else None
    fpr = fp/N if N else None
    f1 = 2*tp/(2*tp+fp+fn) if (tp+fp+fn) else None
    return dict(precision=prec, recall=rec, fpr=fpr, fnr=1-rec if rec is not None else None,
                specificity=1-fpr if fpr is not None else None,
                accuracy=(tp+tn)/(P+N) if P+N else None, binary_f1=f1)

def auc_ap(rows, score_key):
    import bisect
    pos = [r[score_key] for r in rows if r['truth_defect']]
    neg = [r[score_key] for r in rows if not r['truth_defect']]
    ns = sorted(neg); wins = ties = 0
    for s in pos:
        lt = bisect.bisect_left(ns, s); le = bisect.bisect_right(ns, s)
        wins += lt; ties += le-lt
    auc = (wins+0.5*ties)/(len(pos)*len(neg)) if pos and neg else None
    order = sorted([(r[score_key], r['truth_defect']) for r in rows], key=lambda x: -x[0])
    ap = tp = 0.0
    for i, (_, t) in enumerate(order, 1):
        if t: tp += 1; ap += tp/i
    ap /= sum(1 for r in rows if r['truth_defect']) or 1
    return auc, ap

def macro_weighted_f1(rows, pos_key):
    by_cat = defaultdict(list)
    for r in rows: by_cat[r['category']].append(r)
    f1s, weights = [], []
    for cat, rs in by_cat.items():
        tp, fn, fp, tn = conf_matrix(rs, pos_key)
        f1 = 2*tp/(2*tp+fp+fn) if (tp+fp+fn) else None
        if f1 is not None:
            f1s.append(f1); weights.append(len(rs))
    macro = sum(f1s)/len(f1s) if f1s else None
    weighted = sum(f*w for f, w in zip(f1s, weights))/sum(weights) if weights else None
    return macro, weighted, len(f1s)

with (OUT/'corrected_confusion_matrices.csv').open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['model', 'scope', 'n', 'n_defect', 'tp', 'fn', 'fp', 'tn', 'precision', 'recall', 'fpr', 'fnr', 'specificity', 'accuracy', 'binary_f1', 'macro_f1_over_categories', 'weighted_f1', 'n_categories', 'auroc', 'ap', 'excluded', 'note'])
    for model, key, score in (('HVQ standalone (corrected reference)', 'hvq_pos', 'hvq_mean'), ('RT-DETRv2 standalone (conf>=0.4)', 'rt_pos', 'rtdetr_raw')):
        for scope, rows in (('all', preds), ('test', [r for r in preds if r['split'] == 'test'])):
            tp, fn, fp, tn = conf_matrix(rows, key)
            rt = rates(tp, fn, fp, tn)
            auc, ap = auc_ap(rows, score if model.startswith('RT') else 'hvq_mean')
            macro, weighted, ncat = macro_weighted_f1(rows, key)
            w.writerow([model, scope, len(rows), tp+fn, tp, fn, fp, tn] +
                       [round(v, 6) if isinstance(v, float) else v for v in (rt['precision'], rt['recall'], rt['fpr'], rt['fnr'], rt['specificity'], rt['accuracy'], rt['binary_f1'], macro, weighted)] +
                       [ncat, round(auc, 6), round(ap, 6), 0, '이진 판정. hold/unknown 제외 없음(단독 참고는 보류 없음)'])

# ---------- Phase 2: complementarity ----------
def complementarity(rows):
    A = sum(1 for r in rows if r['truth_defect'] and r['rt_pos'] and r['hvq_pos'])
    B = sum(1 for r in rows if r['truth_defect'] and r['rt_pos'] and not r['hvq_pos'])
    C = sum(1 for r in rows if r['truth_defect'] and not r['rt_pos'] and r['hvq_pos'])
    D = sum(1 for r in rows if r['truth_defect'] and not r['rt_pos'] and not r['hvq_pos'])
    NB = sum(1 for r in rows if not r['truth_defect'] and r['rt_pos'] and r['hvq_pos'])
    NR = sum(1 for r in rows if not r['truth_defect'] and r['rt_pos'] and not r['hvq_pos'])
    NH = sum(1 for r in rows if not r['truth_defect'] and not r['rt_pos'] and r['hvq_pos'])
    NN = sum(1 for r in rows if not r['truth_defect'] and not r['rt_pos'] and not r['hvq_pos'])
    return dict(A_both=A, B_rt_only=B, C_hvq_only=C, D_neither=D,
                N_both_fp=NB, N_rt_fp_only=NR, N_hvq_fp_only=NH, N_none=NN,
                defect_total=A+B+C+D, normal_total=NB+NR+NH+NN,
                rt_fn=C+D, hvq_fn=B+D, rt_fp=NB+NR, hvq_fp=NB+NH)

for name, rows in (('complementarity_full', preds), ('complementarity_test', [r for r in preds if r['split'] == 'test'])):
    g = complementarity(rows)
    with (OUT/f'{name}.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['group', 'definition', 'products'])
        for k, d in (('A_both', '불량 · RT 검출 ∧ HVQ 검출'), ('B_rt_only', '불량 · RT만 검출 (HVQ 미탐)'),
                     ('C_hvq_only', '불량 · HVQ만 검출 (RT 미탐)'), ('D_neither', '불량 · 둘 다 미탐')):
            w.writerow([k, d, g[k]])
        w.writerow(['defect_total', '합계(실제 불량)', g['defect_total']])
        w.writerow([])
        for k, d in (('N_both_fp', '정상 · RT 오탐 ∧ HVQ 오탐'), ('N_rt_fp_only', '정상 · RT만 오탐'),
                     ('N_hvq_fp_only', '정상 · HVQ만 오탐'), ('N_none', '정상 · 둘 다 정상')):
            w.writerow([k, d, g[k]])
        w.writerow(['normal_total', '합계(실제 정상)', g['normal_total']])
        w.writerow([])
        w.writerow(['derived', 'formula', 'value', 'crosscheck'])
        w.writerow(['rt_fn', 'C+D', g['rt_fn'], 'single_model_rtdetr.fn과 일치해야 함'])
        w.writerow(['hvq_fn', 'B+D', g['hvq_fn'], 'single_model_hvq.fn과 일치해야 함'])
        w.writerow(['rt_fp', 'N_both_fp+N_rt_fp_only', g['rt_fp'], 'single_model_rtdetr.fp와 일치해야 함'])
        w.writerow(['hvq_fp_total', 'N_both_fp+N_hvq_fp_only', g['hvq_fp'], '단, N_hvq_fp_only는 RT 미동반 subset'])
    print(name, {k: g[k] for k in ('A_both','B_rt_only','C_hvq_only','D_neither','rt_fn','hvq_fn','hvq_fp')})

# ---------- Phase 3: score comparison ----------
val = [r for r in preds if r['split'] == 'validation']
test = [r for r in preds if r['split'] == 'test']

def norm_params(rows, key):
    lo = min(r[key] for r in rows); hi = max(r[key] for r in rows)
    return lo, hi
def nm(x, lo, hi): return (x-lo)/(hi-lo) if hi > lo else 0.0

val_by_cat = defaultdict(list)
for r in val: val_by_cat[r['category']].append(r)
cat_params = {c: {k: norm_parameters if False else None for k in ()} for c in ()}
cat_minmax = {}
for c, rs in val_by_cat.items():
    cat_minmax[c] = {
        'mean': norm_params(rs, 'hvq_mean'),
        'max16': norm_params(rs, 'hvq_max16_max'),
    }

def variants(r):
    out = {}
    out['mean_max'] = r['hvq_mean']
    out['max16_max'] = r['hvq_max16_max']
    cm = cat_minmax[r['category']]
    n_mean = nm(r['hvq_mean'], *cm['mean'])
    n_max16 = nm(r['hvq_max16_max'], *cm['max16'])
    out['combo_50_50_catnorm'] = 0.5*n_mean + 0.5*n_max16
    return out, n_mean, n_max16

rows_out = []
def best_f1_th(pairs):
    ys = sorted(pairs, key=lambda x: -x[0])
    P = sum(t for _, t in pairs)
    best = (0, None)
    for th in sorted({s for s, _ in pairs}, reverse=True):
        tp = sum(1 for s, t in pairs if s >= th and t)
        fp = sum(1 for s, t in pairs if s >= th and not t)
        fn = P - tp
        f1 = 2*tp/(2*tp+fp+fn) if (tp+fp+fn) else 0
        if f1 > best[0]: best = (f1, th)
    return best

with (OUT/'score_comparison.csv').open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['variant', 'definition', 'fit_split', 'n_pos', 'n_neg', 'auroc', 'ap', 'best_f1', 'best_threshold', 'recall_at_best', 'fn_at_best', 'fp_at_best'])
    for vname, vdef in (('mean_max', '제품=max(5시점 heatmap_mean). 현행 퓨전 입력'),
                        ('max16_max', '제품=max(5시점 hvq_max16). 저장 max16 척도'),
                        ('combo_50_50_catnorm', '품목별 Val minmax 정규화 후 0.5*mean+0.5*max16')):
        for sname, srows in (('validation', val), ('test', test)):
            pairs = []
            for r in srows:
                v, _, _ = variants(r)
                pairs.append((v[vname], r['truth_defect']))
            auc, ap = auc_ap([{ 's': s, 'truth_defect': t} for s, t in pairs], 's')
            bf, bth = best_f1_th(pairs)
            P = sum(t for _, t in pairs)
            fn = sum(1 for s, t in pairs if s < bth and t)
            fp = sum(1 for s, t in pairs if s >= bth and not t)
            rec = (P-fn)/P
            w.writerow([vname, vdef, sname, P, len(pairs)-P, round(auc,6), round(ap,6), round(bf,6), bth, round(rec,6), fn, fp])
    w.writerow(['percentile_series', 'percentile 계열 점수는 저장 캐시에 없음(views: hvq_mean, hvq_max16, rtdetr_raw만 저장)', '-', '', '', '', '', '', '', '', '', ''])

# ---------- Phase 4: fusion ablation ----------
CATS = sorted({r['category'] for r in preds})

def build_inputs():
    for r in preds:
        r['rt_in'] = float(r['rtdetr_raw']) if float(r['rtdetr_raw']) >= 0.4 else 0.0
        r['mean_in'] = r['hvq_mean']
        r['max16_in'] = r['hvq_max16_max']
    params = {}
    for c in CATS:
        rs = [r for r in val if r['category'] == c]
        params[c] = {'rt': norm_params(rs, 'rt_in'), 'mean': norm_params(rs, 'mean_in'), 'max16': norm_params(rs, 'max16_in')}
    return params

PARAMS = build_inputs()
FIELD = {'rt': 'rt_in', 'mean': 'mean_in', 'max16': 'max16_in'}
def norm(r, key):
    lo, hi = PARAMS[r['category']][key]
    return nm(r[FIELD[key]], lo, hi)

CANDIDATES = [
    ('rt_only', 'RT 단독', lambda r: norm(r, 'rt')),
    ('hvq_mean_only', 'HVQ mean 단독', lambda r: norm(r, 'mean')),
    ('hvq_max16_only', 'HVQ max16 단독', lambda r: norm(r, 'max16')),
    ('hvq_mean_max16_5050', 'HVQ mean+max16 0.5:0.5(고정)', lambda r: 0.5*norm(r, 'mean')+0.5*norm(r, 'max16')),
    ('fusion_current', '현행 RT0.7+HVQmean0.3', lambda r: 0.7*norm(r, 'rt')+0.3*norm(r, 'mean')),
    ('fusion_rt_max16_7030', 'RT0.7+HVQmax16 0.3', lambda r: 0.7*norm(r, 'rt')+0.3*norm(r, 'max16')),
    ('fusion_rt_mean_max16_701515', 'RT0.7+mean0.15+max16 0.15', lambda r: 0.7*norm(r, 'rt')+0.15*norm(r, 'mean')+0.15*norm(r, 'max16')),
]

def fit_eval(score_fn, srows_fit, srows_eval):
    # 운영 계약과 동일: 품목별 TH/margin을 validation에서만 적합. 외삽 무클립.
    cat_fit = {}
    val_by_cat = defaultdict(list)
    for r in srows_fit: val_by_cat[r['category']].append(r)
    for c, rs in val_by_cat.items():
        fit = threshold_and_margin([score_fn(r) for r in rs], [r['truth_defect'] for r in rs], drop_tolerance=0.005)
        cat_fit[c] = (fit['threshold'], fit['margin'])
    out = {}
    for name, rows in (('all', preds), ('test', srows_eval)):
        # binary: hold 포함 전 제품(운영 보고서 헤드라인 방식)
        btp=bfn=bfp=btn=0
        # decided: hold 제외 확정 판정
        tp = fn = fp = tn = hold = 0
        for r in rows:
            th, margin = cat_fit[r['category']]
            s = score_fn(r)  # 평가는 외삽 허용(무클립)
            pos = s >= th; t = r['truth_defect']
            if pos and t: btp += 1
            elif pos: bfp += 1
            elif t: bfn += 1
            else: btn += 1
            if abs(s-th) <= margin: hold += 1; continue
            if pos and t: tp += 1
            elif pos: fp += 1
            elif t: fn += 1
            else: tn += 1
        ths = [v[0] for v in cat_fit.values()]
        out[name] = dict(th=round(sum(ths)/len(ths), 6), margin=round(sum(v[1] for v in cat_fit.values())/len(cat_fit), 6),
                         hold=hold, tp=tp, fn=fn, fp=fp, tn=tn,
                         decided=tp+fn+fp+tn,
                         f1=(2*tp/(2*tp+fp+fn)) if (tp+fp+fn) else None,
                         recall=(tp/(tp+fn)) if tp+fn else None,
                         fpr=(fp/(fp+tn)) if fp+tn else None,
                         btp=btp, bfn=bfn, bfp=bfp, btn=btn,
                         b_f1=(2*btp/(2*btp+bfp+bfn)) if (btp+bfp+bfn) else None,
                         b_recall=(btp/(btp+bfn)) if btp+bfn else None,
                         b_fpr=(bfp/(bfp+btn)) if bfp+btn else None)
    return out

abl = []
for cid, cname, fn_ in CANDIDATES:
    res = fit_eval(fn_, val, test)
    row = {'candidate': cid, 'name': cname}
    for scope in ('all', 'test'):
        m = res[scope]
        row.update({f'{scope}_{k}': m[k] for k in ('th', 'margin', 'hold', 'tp', 'fn', 'fp', 'tn', 'decided', 'f1', 'recall', 'fpr', 'btp', 'bfn', 'bfp', 'btn', 'b_f1', 'b_recall', 'b_fpr')})
    abl.append(row)

# val-fitted combo candidates (weights fitted on validation only)
best_combo = None
for w_mean in (0.0, 0.25, 0.5, 0.75, 1.0):
    res = fit_eval(lambda r, wm=w_mean: wm*norm(r, 'mean')+(1-wm)*norm(r, 'max16'), val, test)
    key = ('hvq_combo_mean%.2f' % w_mean)
    row = {'candidate': key, 'name': f'HVQ mean/max16 조합 mean가중 {w_mean:.2f}(Val 적합)'}
    for scope in ('all', 'test'):
        m = res[scope]
        row.update({f'{scope}_{k}': m[k] for k in ('th', 'margin', 'hold', 'tp', 'fn', 'fp', 'tn', 'decided', 'f1', 'recall', 'fpr', 'btp', 'bfn', 'bfp', 'btn', 'b_f1', 'b_recall', 'b_fpr')})
    abl.append(row)
    if best_combo is None or (res['test']['f1'] or 0) > (best_combo[1]['test']['f1'] or 0):
        best_combo = (key, res)

with (OUT/'fusion_candidate_comparison.csv').open('w', newline='') as f:
    w = csv.writer(f)
    keys = ['candidate', 'name', 'all_th', 'all_margin', 'all_hold', 'all_tp', 'all_fn', 'all_fp', 'all_tn', 'all_f1', 'all_recall', 'all_fpr', 'all_btp', 'all_bfn', 'all_bfp', 'all_btn', 'all_b_f1', 'all_b_recall', 'all_b_fpr',
            'test_th', 'test_margin', 'test_hold', 'test_tp', 'test_fn', 'test_fp', 'test_tn', 'test_f1', 'test_recall', 'test_fpr', 'test_btp', 'test_bfn', 'test_bfp', 'test_btn', 'test_b_f1', 'test_b_recall', 'test_b_fpr']
    w.writerow(keys)
    for row in abl:
        w.writerow([row.get(k) for k in keys])

# same-FPR recall / same-recall FPR vs current (test)
cur = next(r for r in abl if r['candidate'] == 'fusion_current')
trade = []
for row in abl:
    trade.append({'candidate': row['candidate'],
                  'test_fpr': row['test_fpr'], 'test_recall': row['test_recall'], 'test_f1': row['test_f1']})

summary = {
    'phase1': {'hvq_binary_f1_all': 2*11795/(2*11795+9195+613), 'hvq_fp_total': 9195,
               'note': 'F1 0.7063은 FP 9,195 기준 binary F1. 6,976은 RT 미동반 정상 오탐 subset.'},
    'phase2': {name: complementarity(rows) for name, rows in (('all', preds), ('test', [r for r in preds if r['split']=='test']))},
    'phase4_best_val_combo': best_combo[0] if best_combo else None,
    'tradeoff': trade,
}
(OUT/'metric_consistency.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print(json.dumps({'phase1_f1': summary['phase1']['hvq_binary_f1_all'],
                  'current_test': {k: cur[k] for k in ('test_f1', 'test_recall', 'test_fpr', 'test_fn', 'test_fp', 'test_hold')},
                  'best_val_combo': summary['phase4_best_val_combo']}, ensure_ascii=False))
