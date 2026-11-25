"""명시적 raw map/GT 쌍에만 적용하는 AUPRO. PNG 색상 오버레이는 평가하지 않는다."""
import numpy as np
import cv2

def compute_aupro(pairs, *, max_fpr=.3, max_thresholds=2048):
    if not 0<max_fpr<=1:raise ValueError('max_fpr 범위 오류')
    prepared=[];values=[];regions=background=0
    for mask,score in pairs:
        mask=np.asarray(mask,bool);score=np.asarray(score,float)
        if mask.shape!=score.shape or mask.ndim!=2 or not np.isfinite(score).all():raise ValueError('마스크/map 형상·유한성 오류')
        n,labels=cv2.connectedComponents(mask.astype('uint8'));components=[labels==i for i in range(1,n)]
        prepared.append((mask,score,components));regions+=len(components);background+=int((~mask).sum());values.append(score.ravel())
    if not regions or not background:return {'value':None,'reason':'no_regions_or_background','regions':regions,'background_pixels':background}
    scores=np.concatenate(values);unique=np.unique(scores)
    thresholds=unique if len(unique)<=max_thresholds else np.unique(np.quantile(scores,np.linspace(0,1,max_thresholds)))
    curve=[(0.,0.)]
    for th in thresholds[::-1]:
        fp=0;overlap=[]
        for mask,score,components in prepared:
            prediction=score>=th;fp+=int((prediction & ~mask).sum())
            overlap.extend(float(prediction[c].sum())/int(c.sum()) for c in components)
        curve.append((fp/background,float(np.mean(overlap))))
    # 같은 FPR에서는 가장 높은 PRO를 사용하며 FPR0의 수직 구간 면적은0이다.
    best={}
    for x,y in curve:best[x]=max(y,best.get(x,0.))
    xs=np.array(sorted(best));ys=np.array([best[x] for x in xs]);end=float(np.interp(max_fpr,xs,ys))
    use=xs<max_fpr;x=np.r_[xs[use],max_fpr];y=np.r_[ys[use],end]
    return {'value':float(np.trapezoid(y,x)/max_fpr),'regions':regions,'background_pixels':background,'images':len(prepared),'max_fpr':max_fpr,'thresholds':len(thresholds),'method':'region_macro_PRO_global_pixel_FPR_trapezoid_normalized','approximation':len(unique)>max_thresholds}
