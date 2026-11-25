"""GUI 5시점 추론 러너 — /home/geonug/MV/inference/.venv/bin/python 전용.

백엔드가 작성한 job JSON을 읽어 두 ONNX 모델(RT-DETRv2 640 / HVQ fp16io 224)로
C1~C5를 추론하고, app.gui_fusion 계약으로 제품 판정을 계산해 결과 JSON을 쓴다.
루트 추론 자산(inference.py, inference_hvq.py)은 import만 하고 수정하지 않는다.

사용법: python gui_infer_runner.py --job <job.json> --result <result.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parents[1]
MV_ROOT = Path(__import__("os").environ.get("GUI_MV_ROOT", "/home/geonug/MV")).resolve()
for p in (str(MV_ROOT), str(AGENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import inference as RT  # noqa: E402  (~/MV/inference.py)
import hvq_common as H  # noqa: E402

from app.gui_fusion import EXPECTED_VIEWS, apply_fusion_contract  # noqa: E402


def _save_heatmap_vis(image_path: Path, pred, out_path: Path) -> None:
    """inference_hvq.save_heatmap_vis와 동일 규약의 오버레이 저장."""
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    heat = pred[0].cpu().numpy()
    heat = (heat - heat.min()) / (heat.max() - heat.min() + 1e-9)
    try:
        import matplotlib.cm as cm  # noqa: PLC0415

        rgba = cm.get_cmap("jet")(heat)[..., :3]
    except Exception:  # noqa: BLE001
        rgba = __import__("numpy").stack(
            [heat, __import__("numpy").zeros_like(heat), 1 - heat], axis=-1)
    heat_img = Image.fromarray((rgba * 255).astype("uint8"))
    with Image.open(image_path) as img:
        base = img.convert("RGB").resize(heat_img.size)
    overlay = Image.blend(base, heat_img, alpha=0.45)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    overlay.save(out_path)


def run_job(job: dict) -> dict:
    import numpy as np  # noqa: PLC0415
    import torch  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    item = job["item"]
    views = {k: Path(v) for k, v in sorted(job["views"].items())}
    if sorted(views) != list(EXPECTED_VIEWS):
        raise ValueError(f"C1~C5 5개 시점 이미지가 필요합니다: {sorted(views)}")
    for cam, p in views.items():
        if not p.is_file():
            raise FileNotFoundError(f"{cam} 이미지 없음: {p}")
    out_dir = Path(job["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    contract = job["contract"]

    # --- 모델 준비 (config/fusion.json 경유 상대 경로는 MV 루트 기준) ---
    rt_cfg = contract["rtdetr"]
    hvq_cfg = contract["hvq"]
    rt_onnx = Path(rt_cfg["onnx"])
    if not rt_onnx.is_absolute():
        rt_onnx = MV_ROOT / rt_onnx
    hvq_onnx = Path(hvq_cfg["onnx_fp16"])
    if not hvq_onnx.is_absolute():
        hvq_onnx = MV_ROOT / hvq_onnx
    for p in (rt_onnx, hvq_onnx):
        if not p.is_file():
            raise FileNotFoundError(f"ONNX 모델 없음: {p}")

    ckpt_rt = Path(job.get("rtdetr_checkpoint", MV_ROOT / "epoch_0015.pt"))
    ckpt_hvq = Path(job.get("hvq_checkpoint", MV_ROOT / "hvq_best.pt"))

    rt_engine = RT.ONNXEngine(rt_onnx, RT.count_classes(RT.extract_state_dict(ckpt_rt, use_ema=True)))
    hvq_engine = H.HVQONNXFP16IOEngine(hvq_onnx, 30)
    branch_mapping = H.load_branch_mapping(ckpt_hvq)
    if item not in branch_mapping:
        raise ValueError(f"HVQ 분기 없는 품목: {item}")
    label = branch_mapping[item]

    images: list[Image.Image] = []
    try:
        for cam in EXPECTED_VIEWS:
            with Image.open(views[cam]) as im:
                im.load()
                images.append(im.convert("RGB"))

        with torch.inference_mode():
            # RT-DETR: 제품 단위 배치(5장) — 배치 파이프라인과 동일
            rt_batch = RT.preprocess(images, int(rt_cfg["imgsz"]))
            logits, boxes = rt_engine.infer(rt_batch)
            orig_sizes = torch.tensor([[im.width, im.height] for im in images])
            detections = RT.postprocess(
                logits, boxes, orig_sizes,
                conf=float(rt_cfg["score_floor"]), iou=float(rt_cfg["iou"]),
            )
            # HVQ: 동일 배치, 품목 분기 라벨 고정
            hvq_batch = H.preprocess(images, int(hvq_cfg["imgsz"]))
            pred = hvq_engine.infer(hvq_batch, torch.tensor([label] * 5, dtype=torch.long))
            if not torch.isfinite(pred).all():
                raise ValueError("HVQ 출력 NaN/Inf")
            pooled = torch.nn.functional.avg_pool2d(pred.float(), 16, stride=1)
            max16 = pooled.flatten(1).max(dim=1).values
            hvq_means = H.scores_from_pred(pred).float().tolist()

        per_view: dict[str, dict] = {}
        view_rt_raw: dict[str, float] = {}
        view_hvq16: dict[str, float] = {}
        for cam, im, det, heat, h16, hmean in zip(
            EXPECTED_VIEWS, images, detections, pred, max16.tolist(), hvq_means,
        ):
            dets = [
                {
                    "bbox": [round(float(v), 2) for v in box],
                    "class_id": int(lb),
                    "class_name": rt_engine.class_names[int(lb)]
                    if int(lb) < len(rt_engine.class_names) else str(int(lb)),
                    "score": round(float(sc), 4),
                }
                for box, sc, lb in zip(det["boxes"], det["scores"], det["labels"])
            ]
            stem = f"{cam}"
            heat_png = out_dir / f"{stem}_hvqmap.png"
            map_npy = out_dir / f"{stem}_map.npy"
            _save_heatmap_vis(views[cam], heat, heat_png)
            with map_npy.open("wb") as f:
                np.save(f, heat.float().numpy())
            rt_raw = max((d["score"] for d in dets), default=0.0)
            per_view[cam] = {
                "camera_id": cam,
                "width": im.width,
                "height": im.height,
                "image_path": str(views[cam]),
                "rtdetr_raw": round(rt_raw, 6),
                "hvq_mean": round(float(hmean), 6),
                "hvq_max16": round(float(h16), 6),
                "detections": dets,
                "heatmap_png": str(heat_png),
                "map_npy": str(map_npy),
            }
            view_rt_raw[cam] = rt_raw
            view_hvq16[cam] = float(h16)

        product = apply_fusion_contract(
            item=item, view_rt_raw=view_rt_raw, view_hvq_max16=view_hvq16,
            contract=contract,
        )
        return {
            "ok": True,
            "item": item,
            "product_id": job.get("product_id"),
            "views": per_view,
            "product": product,
            "models": job.get("model_versions", {}),
            "config_version": job.get("config_version"),
            "elapsed_ms": None,
        }
    finally:
        for im in images:
            im.close()
        rt_engine.release()
        hvq_engine.release()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--result", required=True)
    a = ap.parse_args()
    t0 = time.perf_counter()
    result_path = Path(a.result)
    try:
        job = json.loads(Path(a.job).read_text())
        result = run_job(job)
        result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:  # noqa: BLE001
        payload = {"ok": False, "error": f"{type(e).__name__}: {e}",
                   "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1)}
        result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
