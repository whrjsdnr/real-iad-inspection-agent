"""Derive fusion only from an explicitly supplied validation manifest.

No validation products are selected implicitly. Target denominators require confirmation.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import hashlib
import os
import dbconn
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

AGENT_ROOT = Path(__file__).resolve().parent


def _mv_root() -> Path:
    for cand in (AGENT_ROOT.parent / "MV", Path("/home/geonug/MV")):
        if (cand / "inference.py").is_file():
            return cand
    raise FileNotFoundError("MV 루트를 찾지 못했습니다")


MV_ROOT = _mv_root()
sys.path.insert(0, str(MV_ROOT))
sys.path.insert(0, str(AGENT_ROOT))

import fusion  # noqa: E402
from migrate import migrate  # noqa: E402

_CFG = fusion.load_config()
RT_WEIGHT, HVQ_WEIGHT = _CFG["weights"]["rtdetr"], _CFG["weights"]["hvq"]
TARGET = {"recall": 0.938, "f1": 0.9314, "miss": 37, "false_alarm": 46,
          "defect_products": 600}
TOL = _CFG["target"]["tolerance"]
RUN_MODEL_TAG = "fusion-v2:rtdetr-epoch15-fp32+hvq-best-fp16"


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# 1. val 세트 선정
# ---------------------------------------------------------------------------
def select_val_products(dataset: Path, manifest: Path) -> dict[str, dict]:
    """Read an explicit CSV: product_id,item,truth,camera,image_path.

    Folder-based identity must be confirmed before producing this manifest.
    """
    if not manifest or not Path(manifest).is_file():
        raise ValueError("원본 validation manifest가 필요합니다; 자동 표본 선정은 금지됩니다")
    val = {}
    with Path(manifest).open(newline="") as f:
        for row in csv.DictReader(f):
            if row["truth"] not in ("normal", "defect"):
                raise ValueError("Invalid validation truth")
            p = val.setdefault(row["product_id"], {"item": row["item"],
                              "truth": row["truth"], "views": {}})
            if p["truth"] != row["truth"] or p["item"] != row["item"]:
                raise ValueError("Inconsistent product labels")
            cam = row["camera"]
            path = dataset / row["image_path"]
            if cam in p["views"] or not path.is_file():
                raise ValueError("Duplicate view or missing image")
            p["views"][cam] = str(path)
    expected = set(_CFG["capture"]["expected_views"])
    if any(set(p["views"]) != expected for p in val.values()):
        raise ValueError("Validation requires exactly C1-C5 per product")
    if len(val) != _CFG["calibration"]["expected_products"]:
        raise ValueError("Validation product count differs from configured 120 products")
    return val


# ---------------------------------------------------------------------------
# 2. 점수 생성 (캐시 재사용)
# ---------------------------------------------------------------------------
def load_shared():
    spec = importlib.util.spec_from_file_location("rt_pipeline_shared", MV_ROOT / "inference.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ensure_scores(args, val: dict[str, dict]) -> Path:
    cache = Path(args.scores_cache)
    manifest_hash = hashlib.sha256(Path(args.val_manifest).read_bytes()).hexdigest()
    provenance = {"manifest_sha256": manifest_hash, "score_variant": "heatmap_mean",
                  "model_versions": _CFG["model_versions"]}
    meta = cache.with_suffix(cache.suffix + ".provenance.json")
    if cache.exists() and not args.regen:
        if not meta.exists() or json.loads(meta.read_text()) != provenance:
            raise ValueError("점수 캐시의 검증 목록/모델/점수 정의 출처가 다릅니다; --regen 필요")
        rows = load_scores(cache)
        expected = {(pid, cam, p["truth"]) for pid, p in val.items() for cam in p["views"]}
        actual = {(r["product_id"], r["camera"], r["truth"]) for r in rows}
        if actual != expected or len(rows) != len(expected):
            raise ValueError("점수 캐시의 제품/시점/GT가 원본 Val과 다릅니다")
        log(f"[derive] 점수 캐시 재사용: {cache}")
        return cache

    import torch  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    import onnxruntime as ort  # noqa: PLC0415

    shared = load_shared()
    import hvq_common as H  # noqa: PLC0415

    from batch_fusion import RTORTEngine  # 지연 임포트

    so_rt = ort.SessionOptions()
    so_rt.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so_rt.intra_op_num_threads = int(_CFG["runner"]["rtdetr_threads"])
    so_rt.inter_op_num_threads = 1
    rt = RTORTEngine(MV_ROOT / "rtdetr_outputs" / "epoch_0015_640.onnx",
                     shared.count_classes(shared.extract_state_dict(
                         MV_ROOT / "epoch_0015.pt", use_ema=True)),
                     session_options=so_rt)
    so_hv = ort.SessionOptions()
    so_hv.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so_hv.intra_op_num_threads = int(_CFG["runner"]["hvq_threads"])
    so_hv.inter_op_num_threads = 1
    hvq = H.HVQONNXFP16IOEngine(MV_ROOT / "hvq_outputs" / "hvq_best.fp16io.onnx",
                                30, session_options=so_hv)
    bm = H.load_branch_mapping(MV_ROOT / "hvq_best.pt")

    rows = []
    t0 = time.time()
    pids = sorted(val)
    for i, pid in enumerate(pids, 1):
        views = val[pid]["views"]
        paths = [views[c] for c in sorted(views)]
        pil = [Image.open(p).convert("RGB") for p in paths]
        orig = torch.tensor([[im.width, im.height] for im in pil])
        with torch.no_grad():
            logits, boxes = rt.infer(shared.preprocess(pil, 640))
        dets = shared.postprocess(logits, boxes, orig, conf=_CFG["rtdetr"]["score_floor"], iou=_CFG["rtdetr"]["iou"])
        labels = H.labels_for_images(paths, bm, default=val[pid]["item"])
        hpred = hvq.infer(H.preprocess(pil, 224), labels)
        hvq_scores = [float(x) for x in H.scores_from_pred(hpred)]
        for (cam, path), det, hs in zip(sorted(views.items()), dets, hvq_scores):
            rt_conf = max([float(s) for s in det["scores"]], default=0.0)
            rows.append({"product_id": pid, "item": val[pid]["item"],
                         "truth": val[pid]["truth"], "camera": cam,
                         "rt_conf": rt_conf,
                         "hvq_score": hs})
        for im in pil:
            im.close()
        if i % 120 == 0:
            el = time.time() - t0
            log(f"[derive] {i}/{len(pids)} 제품 ({el/60:.1f}분, "
                f"잔여 ETA {(len(pids)-i)/(i/el)/60:.1f}분)")
    rt.release()
    hvq.release()
    with cache.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["product_id", "item", "truth", "camera",
                                          "rt_conf", "hvq_score"])
        w.writeheader()
        w.writerows(rows)
    meta.write_text(json.dumps(provenance, indent=2))
    log(f"[derive] 점수 저장: {cache} ({len(rows)}행, {time.time()-t0:.0f}s)")
    return cache


# ---------------------------------------------------------------------------
# 3~5. 정규화/집계/TH
# ---------------------------------------------------------------------------
def load_scores(cache: Path) -> list[dict]:
    with cache.open() as f:
        return list(csv.DictReader(f))


def minmax_stats(rows: list[dict]) -> dict:
    rt = np.array([float(r["rt_conf"]) for r in rows])
    hv = np.array([float(r["hvq_score"]) for r in rows])
    return {
        "rt": {"min": float(rt.min()), "max": float(rt.max())},
        "hvq": {"min": float(hv.min()), "max": float(hv.max())},
    }


def norm(v: float, s: dict) -> float:
    return (v - s["min"]) / (s["max"] - s["min"]) if s["max"] > s["min"] else 0.0


def product_scores(rows: list[dict], stats: dict, agg: str) -> dict[str, dict]:
    """제품 단위 가중합 점수. agg: 'mean' | 'max'."""
    prods: dict[str, dict] = {}
    for r in rows:
        comb = RT_WEIGHT * norm(float(r["rt_conf"]), stats["rt"]) + \
            HVQ_WEIGHT * norm(float(r["hvq_score"]), stats["hvq"])
        p = prods.setdefault(r["product_id"], {"item": r["item"], "truth": r["truth"],
                                               "view_scores": []})
        p["view_scores"].append(comb)
    for pid, p in prods.items():
        p["score"] = float(np.mean(p["view_scores"])) if agg == "mean" \
            else float(np.max(p["view_scores"]))
    return prods


def sweep_f1(prods: dict[str, dict]) -> list[dict]:
    """TH 스윕 → F1/Recall/FPR 표."""
    scores = sorted({p["score"] for p in prods.values()})
    P = sum(1 for p in prods.values() if p["truth"] == "defect")
    N = len(prods) - P
    out = []
    for th in scores:
        tp = sum(1 for p in prods.values() if p["truth"] == "defect" and p["score"] >= th)
        fp = sum(1 for p in prods.values() if p["truth"] == "normal" and p["score"] >= th)
        fn = P - tp
        rec = tp / P if P else 0.0
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
        out.append({"th": th, "tp": tp, "fp": fp, "fn": fn,
                    "recall": rec, "fpr": fp / N if N else 0.0, "f1": f1})
    return out


def best_threshold(curve: list[dict]) -> dict:
    b = max(curve, key=lambda r: r["f1"])
    return dict(b)


def margin_around(curve: list[dict], best: dict, tol: float = 0.005) -> float:
    """F1 하락 tol 이내인 최대 대칭 폭(±m)."""
    target = best["f1"] - tol
    cands = [r for r in curve if r["f1"] >= target]
    if not cands:
        return 0.0
    lo, hi = min(c["th"] for c in cands), max(c["th"] for c in cands)
    # best TH 중심 대칭 폭: 한쪽으로 벌릴 수 있는 최대
    return round(min(best["th"] - lo, hi - best["th"]), 5)


# ---------------------------------------------------------------------------
# 8. 설정 저장 + DB 기준선
# ---------------------------------------------------------------------------
def save_derived(out_path: Path, payload: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    log(f"[derive] 설정 저장 → {out_path}")


def register_baseline(db_path: Path, payload: dict) -> None:
    os.environ.setdefault("DATABASE_URL", "sqlite:///" + str(db_path.resolve()))
    migrate()
    from metrics import save_snapshot
    d = payload["derived"]
    entries = [("fusion_val_recall", d["tp"], d["tp"] + d["fn"]),
               ("fusion_val_f1", 2*d["tp"], 2*d["tp"] + d["fp"] + d["fn"]),
               ("fusion_val_miss", d["fn"], d["tp"] + d["fn"]),
               ("fusion_val_false_alarm", d["fp"], payload["val_normal_products"])]
    for metric, num, den in entries:
        save_snapshot(metric=metric, num=num, den=den, value=num/den if den else None,
                      model_version=RUN_MODEL_TAG, reason="baseline-v1; " + payload["val_definition"])


# ---------------------------------------------------------------------------
def parse_args(argv=None):
    p = argparse.ArgumentParser(description="퓨전 파라미터 val 도출")
    p.add_argument("--dataset", default=str(MV_ROOT / "dataset"))
    p.add_argument("--val-manifest", required=True, type=Path, help="원본 validation 목록 CSV")
    p.add_argument("--scores-cache", default=str(AGENT_ROOT / "fusion_val_scores.csv"))
    p.add_argument("--out", default=str(AGENT_ROOT / "config" / "fusion.json"))
    p.add_argument("--db", default=str(AGENT_ROOT / "inspection.db"))
    p.add_argument("--regen", action="store_true", help="점수 캐시 무시 재생성")
    return p.parse_args(argv)


def main(argv=None) -> int:
    raise RuntimeError("구형 min-max/평균 집계 보정은 확정 명세와 달라 비활성화했습니다. 검증된 점수/분할로 reconstruct_fusion.py를 사용하세요.")
    args = parse_args(argv)
    log(f"[derive] 가중치 RT:{RT_WEIGHT} / HVQ:{HVQ_WEIGHT}, 목표 Recall={TARGET['recall']} "
        f"F1={TARGET['f1']} (±{TOL:.0%}p)")

    val = select_val_products(Path(args.dataset), args.val_manifest)
    n_def = sum(1 for v in val.values() if v["truth"] == "defect")
    n_norm = len(val) - n_def
    log(f"[derive] val 세트: 제품 {len(val)}개 (불량 {n_def} / 정상 {n_norm}), "
        f"뷰 {sum(len(v['views']) for v in val.values())}장")

    cache = ensure_scores(args, val)
    rows = load_scores(cache)
    stats = minmax_stats(rows)
    log(f"[derive] 정규화 통계: rt=[{stats['rt']['min']:.3f},{stats['rt']['max']:.3f}] "
        f"hvq=[{stats['hvq']['min']:.2f},{stats['hvq']['max']:.2f}]")

    candidates = {}
    for agg in ("mean", "max"):
        prods = product_scores(rows, stats, agg)
        curve = sweep_f1(prods)
        best = best_threshold(curve)
        dist = abs(best["f1"] - TARGET["f1"])
        candidates[agg] = {"prods": prods, "curve": curve, "best": best, "dist": dist}
        log(f"[derive] 집계={agg:4s} → TH={best['th']:.4f} F1={best['f1']:.4f} "
            f"Recall={best['recall']:.4f} FP={best['fp']} FN={best['fn']} "
            f"(목표 F1과 차이 {dist:.4f})")

    agg = min(candidates, key=lambda k: candidates[k]["dist"])
    chosen = candidates[agg]
    best = chosen["best"]
    margin = margin_around(chosen["curve"], best, _CFG["calibration"]["f1_drop_tolerance"])
    log(f"[derive] 채택 집계: {agg} (목표 F1 근접도 기준), margin=±{margin}")

    recall_ok = abs(best["recall"] - TARGET["recall"]) <= TOL
    f1_ok = abs(best["f1"] - TARGET["f1"]) <= TOL
    consistent = recall_ok and f1_ok

    payload = {
        **_CFG,
        "calibration_status": "derived",
        "provenance": {"manifest": str(args.val_manifest), "manifest_sha256": hashlib.sha256(args.val_manifest.read_bytes()).hexdigest()},
        "version": "fusion-derived-v1",
        "derived_at": datetime.now().isoformat(timespec="seconds"),
        "val_definition": str(args.val_manifest),
        "val_products": len(val), "val_defect_products": n_def,
        "val_normal_products": n_norm,
        "weights": {"rtdetr": RT_WEIGHT, "hvq": HVQ_WEIGHT},
        "score_norm": stats,
        "score_definition": {
            "rtdetr": "뷰 내 최대 박스 conf(postprocess conf>=0.05, 없으면 0)",
            "hvq": "heatmap_mean — optimization_report_hvq.md",
            "normalize": "val 뷰 점수 min-max",
            "view_combine": "0.7*rt_norm + 0.3*hvq_norm",
            "product_agg": agg,
        },
        "derived": {"th": best["th"], "margin": margin,
                    "tp": best["tp"], "fp": best["fp"], "fn": best["fn"],
                    "recall": round(best["recall"], 5), "fpr": round(best["fpr"], 5),
                    "f1": round(best["f1"], 5)},
        "target": {**TARGET, "recall_derived": round(best["recall"], 5),
                   "f1_derived": round(best["f1"], 5),
                   "miss_derived": best["fn"], "false_alarm_derived": best["fp"],
                   "within_tolerance": consistent,
                   "note": "재현 일치" if consistent else
                           "재현 불일치 — 집계 재시도 후에도 불일치 시 사실대로 보고, "
                           "도출값으로 진행(임의 수치 조정 없음)"},
        "model_versions": {"rtdetr": "rtdetr-epoch15-onnx-fp32",
                           "hvq": "hvq-best-onnx-fp16"},
        "reproduction_check": {
            "tolerance": TOL,
            "recall_ok": recall_ok, "f1_ok": f1_ok,
            "alt_agg": {k: {"th": v["best"]["th"], "f1": v["best"]["f1"],
                            "recall": v["best"]["recall"]} for k, v in candidates.items()},
        },
    }
    save_derived(Path(args.out), payload)
    register_baseline(Path(args.db), payload)

    print("\n[재현 비교 표]")
    print(f"{'지표':10s} {'목표':>10s} {'도출':>10s} {'차이':>10s} 판정")
    print("-" * 50)
    print(f"{'Recall':10s} {TARGET['recall']:>10.4f} {best['recall']:>10.4f} "
          f"{best['recall']-TARGET['recall']:>+10.4f} {'OK' if recall_ok else '불일치'}")
    print(f"{'F1':10s} {TARGET['f1']:>10.4f} {best['f1']:>10.4f} "
          f"{best['f1']-TARGET['f1']:>+10.4f} {'OK' if f1_ok else '불일치'}")
    print(f"{'미탐':10s} {'37/600':>10s} {best['fn']:>4d}/{n_def:<5d} {best['fn']-37:>+10d}")
    print(f"{'오탐':10s} {'46/600':>10s} {best['fp']:>4d}/{n_norm:<5d} {best['fp']-46:>+10d}")
    if not consistent:
        print("[derive] ⚠️ 목표 재현 불일치 — 원인 추정: val 세트 구성(제품 선정) 또는 "
              "점수 정의(뷰 conf 집계/HVQ 스코어 변형)가 이전 실험과 다를 수 있음. "
              "사실대로 기록하고 도출값으로 진행.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
