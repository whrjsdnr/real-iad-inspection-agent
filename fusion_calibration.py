"""신규 재구성 실험 전용. 원 실험 재현과 구분하며 Test는 보정에 쓰지 않는다."""
from __future__ import annotations
from collections import defaultdict
import math
import numpy as np


def finite(values):
    a = np.asarray(values, dtype=float)
    if a.ndim != 1 or not len(a) or not np.isfinite(a).all():
        raise ValueError('유한한 1차원 점수가 필요합니다')
    return a


def percentile_lookup(values):
    """Val 중간순위 확률: (평균순위-0.5)/n. 순위는 1부터 시작한다.

    최솟값/최댓값 자체는 Val 중간순위 확률, 범위 밖은 각각0/1이다.
    동점과 전체 상수 분포도 이 정의를 그대로 적용한다(상수의 확률0.5).
    """
    a = finite(values)
    unique, counts = np.unique(a, return_counts=True)
    ranks = np.cumsum(counts) - (counts - 1) / 2
    return {'x': unique.tolist(), 'p': ((ranks - .5) / len(a)).tolist(),
            'n': len(a), 'rule': '(average_rank_1based-0.5)/n',
            'ties': 'average_rank', 'interpolation': 'linear', 'outside': [0, 1]}


def percentile(values, lookup):
    a = finite(values)
    x, p = finite(lookup['x']), finite(lookup['p'])
    if len(x) != len(p) or np.any(np.diff(x) <= 0) or np.any(np.diff(p) < 0) or np.any((p < 0) | (p > 1)):
        raise ValueError('잘못된 백분위 lookup')
    return np.interp(a, x, p, left=0., right=1.)


def product_scores(rows, expected_views=('C1', 'C2', 'C3', 'C4', 'C5')):
    """엄격한 제품 키/시점/분할 검사. 누락 점수나 누락 시점은 0으로 대체하지 않는다."""
    groups = defaultdict(list)
    for r in rows:
        groups[r['product_id']].append(r)
    products = []
    for pid, views in sorted(groups.items()):
        if len(views) != len(expected_views) or {r['camera'] for r in views} != set(expected_views):
            raise ValueError(f'{pid}: 시점 누락/중복')
        for field in ['category', 'truth', 'split']:
            if len({r[field] for r in views}) != 1:
                raise ValueError(f'{pid}: {field} 불일치/분할 누수')
        if views[0]['truth'] not in ('normal', 'defect'):
            raise ValueError(f'{pid}: GT 미확정')
        products.append({k: views[0][k] for k in ['product_id', 'category', 'truth', 'split']} |
                        {m: float(finite([r[m] for r in views]).max()) for m in ['hvq', 'rtdetr']})
    return products


def confusion(truth, predicted):
    t = np.asarray(truth, dtype=bool); p = np.asarray(predicted, dtype=bool)
    if t.shape != p.shape: raise ValueError('GT/예측 길이 불일치')
    tp, fn = int((t & p).sum()), int((t & ~p).sum())
    fp, tn = int((~t & p).sum()), int((~t & ~p).sum())
    def ratio(n, d): return {'num': n, 'den': d, 'rate': n / d if d else None}
    return {'tp': tp, 'fn': fn, 'fp': fp, 'tn': tn,
            'recall': ratio(tp, tp+fn), 'fpr': ratio(fp, fp+tn),
            'precision': ratio(tp, tp+fp), 'f1': ratio(2*tp, 2*tp+fp+fn)}


def threshold_and_margin(scores, truth, *, drop_tolerance):
    """F1 일정 구간을 정확히 분석한다. 최적 구간 tie는 가장 높은 구간의 중점.

    판정이 score>=TH이므로 각 구간은 (직전 관측값, 현재 관측값]이다.
    허용 평탄 구간 중 기준TH를 포함한 연결 성분만 취하고, 대칭 margin은
    두 경계까지 거리의 최솟값이다. 열린 하한에 닿으면 nextafter로 안쪽을 쓴다.
    """
    a = finite(scores); t = np.asarray(truth, dtype=bool)
    if len(a) != len(t) or set(t.tolist()) != {False, True}:
        raise ValueError('NG/OK 두 클래스가 모두 필요합니다')
    if np.any((a < 0) | (a > 1)) or not 0 <= drop_tolerance <= 1:
        raise ValueError('잘못된 점수/허용 감소폭')
    ends = np.unique(np.r_[a, 1.]); curve=[]; lower=0.
    for i, upper in enumerate(ends):
        metric=confusion(t, a >= upper)
        curve.append({'lower': float(lower), 'upper': float(upper), 'lower_closed': i == 0,
                      'f1': metric['f1']['rate'], 'counts': metric})
        lower=float(upper)
    best=max(r['f1'] for r in curve)
    selected=max(i for i,r in enumerate(curve) if r['f1'] == best)
    cell=curve[selected]; th=(cell['lower']+cell['upper'])/2
    if th == cell['lower'] and not cell['lower_closed']: th=cell['upper']
    left=right=selected
    while left and curve[left-1]['f1'] >= best-drop_tolerance: left-=1
    while right+1<len(curve) and curve[right+1]['f1'] >= best-drop_tolerance: right+=1
    lo,hi=curve[left]['lower'],curve[right]['upper']
    margin=min(th-lo,hi-th)
    if margin and not curve[left]['lower_closed'] and margin == th-lo:
        margin=float(np.nextafter(margin,0.))
    return {'threshold': th, 'f1': best, 'margin': margin, 'plateau_lower': lo,
            'plateau_upper': hi, 'plateau_lower_closed': curve[left]['lower_closed'],
            'plateau_width': hi-lo, 'symmetric_width': 2*margin,
            'asymmetric_width_discarded': hi-lo-2*margin,
            'tie_break': 'highest_optimal_interval_midpoint', 'curve': curve,
            'hold': {'num': int((np.abs(a-th)<=margin).sum()), 'den': len(a)}}


def fit(products, *, weights, drop_tolerance, minimum_products, minimum_per_class):
    if any(r['split'] != 'validation' for r in products):
        raise ValueError('보정에는 validation만 사용할 수 있습니다')
    if weights != {'hvq': .3, 'rtdetr': .7}: raise ValueError('확정 가중치와 다름')
    if len({r['product_id'] for r in products}) != len(products):raise ValueError('중복 제품')
    bycat=defaultdict(list)
    for p in products:bycat[p['category']].append(p)
    result={}
    for cat,rows in bycat.items():
        truth=[r['truth']=='defect' for r in rows]; n=len(rows); ng=sum(truth)
        if n<minimum_products or min(ng,n-ng)<minimum_per_class:
            result[cat]={'status':'UNCONFIGURED','n':n,'ng':ng,'ok':n-ng,'reason':'insufficient_validation_support'};continue
        lookups={m:percentile_lookup([r[m] for r in rows]) for m in weights}
        score=sum(weights[m]*percentile([r[m] for r in rows],lookups[m]) for m in weights)
        result[cat]={'status':'CONFIGURED','n':n,'ng':ng,'ok':n-ng,'lookups':lookups,
                     **threshold_and_margin(score,truth,drop_tolerance=drop_tolerance)}
    return {'reproduction_status':'RECONSTRUCTED','provenance':'newly_derived',
            'aggregation':'model_view_max_then_percentile_then_weighted_sum','weights':weights,
            'validation_product_ids':sorted(r['product_id'] for r in products),'categories':result}


def predict(product, fitted, *, evaluation=False):
    if evaluation and product['product_id'] in fitted['validation_product_ids']:
        raise ValueError('평가 제품이 calibration과 겹침')
    cat=fitted['categories'].get(product['category'],{})
    if cat.get('status')!='CONFIGURED':return {'status':'UNCONFIGURED','score':None,'verdict':None}
    score=sum(fitted['weights'][m]*float(percentile([product[m]],cat['lookups'][m])[0]) for m in fitted['weights'])
    binary='defect' if score>=cat['threshold'] else 'normal'
    verdict='hold' if abs(score-cat['threshold'])<=cat['margin'] else binary
    return {'status':'CONFIGURED','score':score,'binary_verdict':binary,'verdict':verdict}
