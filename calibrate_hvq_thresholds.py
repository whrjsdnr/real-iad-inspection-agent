"""HVQ 임계값 교정 — 정상(OK) 제품 점수 분포의 p99로 품목별 임계값 산정.

근거(스펙): 'hvq 이상 점수≥임계값(임계값은 기존 튜닝 결과 또는 정상 학습 데이터 분포의 p99로 산정, 근거 기록)'
- checkpoint validation.threshold는 트레이너의 점수 체계(미확정) 기반이며, EvalImageMax(avgpool16) 스케일로
  적용하면 OK 오탐이 과다함이 파일럿에서 확인됨 → 정상 분포 p99 방식을 근거로 채택.
- 산출: config/hvq_thresholds.json {item: {threshold, p99, n_products, score_variant, source, calibrated_at}}

  inference/.venv/bin/python calibrate_hvq_thresholds.py [--per-item 60]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from datetime import datetime
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parent


def _mv_root() -> Path:
    for cand in (AGENT_ROOT.parent / "MV", Path("/home/geonug/MV")):
        if (cand / "hvq_common.py").is_file():
            return cand
    raise FileNotFoundError("MV 루트를 찾지 못했습니다")


MV_ROOT = _mv_root()
sys.path.insert(0, str(MV_ROOT))
import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

import fusion  # noqa: E402
import hvq_common as H  # noqa: E402

SCORE_VARIANT = "max_avgpool16"

score_max16 = fusion.score_max16  # fusion.py이 단일 정의점


def collect_ok_products(dataset: Path, per_item: int, seed: int = 42) -> dict[str, list[str]]:
    """품목당 최대 per_item개의 OK 제품(5시점 대표 경로 1개)을 샘플링."""
    import random as _r

    rng = _r.Random(seed)
    by_item: dict[str, set[str]] = {}
    for p in sorted((dataset).rglob("*.jpg")):
        info = fusion.parse_view_filename(p.name)
        if info is None or info["truth_label"] != "normal":
            continue
        by_item.setdefault(info["item"], set()).add(info["product_id"])
    out = {}
    for item, pids in sorted(by_item.items()):
        pids = sorted(pids)
        rng.shuffle(pids)
        out[item] = pids[:per_item]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(MV_ROOT / "dataset"))
    ap.add_argument("--per-item", type=int, default=60)
    ap.add_argument("--config", default=str(AGENT_ROOT / "config" / "fusion.json"))
    ap.add_argument("--out", default=str(AGENT_ROOT / "config" / "hvq_thresholds.json"))
    args = ap.parse_args(argv)

    cfg = fusion.load_config(Path(args.config))
    hvq_cfg = cfg["hvq"]
    import onnxruntime as ort  # noqa: PLC0415

    so = ort.SessionOptions()
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = 4
    so.inter_op_num_threads = 1
    onnx_path = MV_ROOT / (hvq_cfg["onnx_fp16"] if hvq_cfg["use_fp16"] else hvq_cfg["onnx_fp32"])
    engine = H.HVQONNXFP16IOEngine(onnx_path, 30, session_options=so) \
        if hvq_cfg["use_fp16"] else H.HVQONNXEngine(onnx_path, 30, session_options=so)
    bm = H.load_branch_mapping(MV_ROOT / "hvq_best.pt")

    ok = collect_ok_products(Path(args.dataset), args.per_item)
    # 제품 ID → 대표 이미지 경로 1개(어느 시점이든 정상 분포 동일 가정)
    pid_path: dict[str, Path] = {}
    for p in sorted(Path(args.dataset).rglob("*.jpg")):
        info = fusion.parse_view_filename(p.name)
        if info and info["product_id"] not in pid_path:
            pid_path[info["product_id"]] = p

    results: dict[str, dict] = {}
    t0 = time.time()
    for item, pids in sorted(ok.items()):
        scores = []
        for start in range(0, len(pids), 16):
            batch_pids = pids[start:start + 16]
            paths = [pid_path[pid] for pid in batch_pids if pid in pid_path]
            if not paths:
                continue
            from PIL import Image  # noqa: PLC0415

            pil = [Image.open(p).convert("RGB") for p in paths]
            labels = H.labels_for_images(paths, bm, default=item)
            pred = engine.infer(H.preprocess(pil, 224), labels)
            scores.extend(float(v) for v in score_max16(pred))
            for im in pil:
                im.close()
        if not scores:
            continue
        arr = np.array(scores)
        p99 = float(np.percentile(arr, 99))
        results[item] = {
            "threshold": round(p99, 4),
            "p99": round(p99, 4),
            "p95": round(float(np.percentile(arr, 95)), 4),
            "n_products": len(scores),
            "score_variant": SCORE_VARIANT,
            "score_mean": round(float(arr.mean()), 4),
            "score_max": round(float(arr.max()), 4),
            "source": "ok_distribution_p99",
            "calibrated_at": datetime.now().isoformat(timespec="seconds"),
        }
        print(f"[calib] {item:15s} n={len(scores):4d} p95={results[item]['p95']:7.2f} "
              f"p99={p99:7.2f} max={results[item]['score_max']:7.2f}", flush=True)
    engine.release()

    out = {
        "version": "hvq-thresholds-v1",
        "score_variant": SCORE_VARIANT,
        "per_item": args.per_item,
        "items": results,
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"[calib] 저장 → {args.out} ({len(results)}개 품목, {time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
