"""12만 장 퓨전 배치 러너 (재시작 가능, Ctrl+C 후 이어서 동작).

  inference/.venv/bin/python batch_fusion.py --dataset <Real-IAD 폴드> [--limit 100]

- 제품 ID 단위로 C1–C5 묶음 → RT-DETR(FP32 ONNX) + HVQ(FP16 ONNX) 추론 → 퓨전 판정
- 완료 제품은 스킵(재실행 시 이어서), 실패 건은 상태+사유 기록(촬영·처리 실패율 분자)
- 진행률·ETA·처리량 주기적 출력, per-product 지연 추적(p95 보고)
- DB 쓰기는 표준 sqlite3 (~/agent/.venv SQLAlchemy와 동일 파일 공유)
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


def _find_mv_root() -> Path:
    for cand in (AGENT_ROOT.parent / "MV", AGENT_ROOT.parent, AGENT_ROOT.parent.parent / "MV"):
        if (cand / "inference.py").is_file() and (cand / "hvq_common.py").is_file():
            return cand
    raise FileNotFoundError("MV 저장소 루트(inference.py/hvq_common.py)를 찾지 못했습니다")


MV_ROOT = _find_mv_root()
if str(MV_ROOT) not in sys.path:
    sys.path.insert(0, str(MV_ROOT))

import numpy as np  # noqa: E402
from sqlalchemy import text

import dbconn  # noqa: E402
import fusion  # noqa: E402
from migrate import migrate  # noqa: E402
from fusion import ROIMapper  # noqa: E402,F401  (batch_fusion이 재노출)


def load_inference_shared():
    spec = importlib.util.spec_from_file_location("rt_pipeline_shared", MV_ROOT / "inference.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


shared = load_inference_shared()
import hvq_common as H  # noqa: E402


def log(msg: str) -> None:
    print(msg, flush=True)


class RTORTEngine:
    """RT-DETR ORT 엔진 (세션 옵션 지원). inference.py의 ONNXEngine과 동일 계약."""

    name = "onnx"

    def __init__(self, onnx_path, num_classes, session_options=None):
        import onnxruntime  # noqa: PLC0415

        self.session = onnxruntime.InferenceSession(
            str(onnx_path), providers=["CPUExecutionProvider"], sess_options=session_options)
        self.num_classes = num_classes
        self.class_names = shared.load_class_names(num_classes)
        self._in = self.session.get_inputs()[0].name

    def infer(self, batch):
        import torch  # noqa: PLC0415

        out = self.session.run(None, {self._in: batch.numpy()})
        return torch.from_numpy(out[0]), torch.from_numpy(out[1])

    def release(self):
        del self.session


RUN_TAG = "fusion-v2:rtdetr-epoch15-fp32+hvq-best-fp16"


# ---------------------------------------------------------------------------
# 데이터셋 스캔
# ---------------------------------------------------------------------------
def scan_dataset(dataset: Path) -> tuple[dict, dict]:
    """제품 ID 단위 묶음. 반환: (products, stats)."""
    products: dict[str, dict] = {}
    stats = {"files": 0, "unparsed": 0, "views": 0}
    for p in sorted(dataset.rglob("*.jpg")):
        stats["files"] += 1
        info = fusion.parse_view_filename(p.name)
        if info is None:
            stats["unparsed"] += 1
            continue
        pid = info["product_id"]
        prod = products.setdefault(pid, {
            "item": info["item"], "truth_label": info["truth_label"],
            "views": {}, "defects": set(),
        })
        if info["defect"]:
            prod["defects"].add(info["defect"])
        prod["views"].setdefault(info["camera"], str(p))
        stats["views"] += 1
    return products, stats


# ---------------------------------------------------------------------------
# DB (SQLAlchemy 엔진 공용 추상화 — PG/SQLite 공통)
# ---------------------------------------------------------------------------
UPSERT_ATTEMPT = text("""
INSERT INTO inspection_attempts
 (attempt_id, product_id, item, started_at, status, model_version, mapping_version,
  verdict, review_status, truth_label, processed_at)
VALUES (:attempt_id, :product_id, :item, :started_at, :status, :model_version,
        :mapping_version, :verdict, 'none', :truth_label, :processed_at)
ON CONFLICT(attempt_id) DO UPDATE SET
  status=excluded.status, verdict=excluded.verdict, truth_label=excluded.truth_label,
  processed_at=excluded.processed_at
""")

UPSERT_VIEW = text("""
INSERT INTO inspection_views
 (view_id, attempt_id, product_id, item, camera_id, image_uri, error_map_uri,
  status, model_version, mapping_version, width, height)
VALUES (:view_id, :attempt_id, :product_id, :item, :camera_id, :image_uri,
        :error_map_uri, :status, :model_version, :mapping_version, :width, :height)
ON CONFLICT(view_id) DO UPDATE SET
  error_map_uri=excluded.error_map_uri, status=excluded.status,
  width=excluded.width, height=excluded.height
""")

UPSERT_FINDING = text("""
INSERT INTO findings
 (finding_id, view_id, product_id, item, camera_id, source, kind,
  bbox_x1, bbox_y1, bbox_x2, bbox_y2, score, part_id,
  model_version, mapping_version, map_uri, meta_json)
VALUES (:finding_id, :view_id, :product_id, :item, :camera_id, :source, :kind,
        :x1, :y1, :x2, :y2, :score, :part_id,
        :model_version, :mapping_version, :map_uri, :meta_json)
ON CONFLICT(finding_id) DO UPDATE SET
  score=excluded.score, map_uri=excluded.map_uri, meta_json=excluded.meta_json
""")


def load_done(run_tag: str) -> set[str]:
    rows = dbconn.query(
        "SELECT product_id FROM inspection_attempts "
        "WHERE model_version=:tag AND status='completed'", {"tag": run_tag})
    return {r["product_id"] for r in rows}


def write_attempt(con, *, attempt_id, product_id, item, status, verdict, truth_label,
                  model_version, mapping_version, started_at, processed_at):
    con.execute(UPSERT_ATTEMPT, dict(
        attempt_id=attempt_id, product_id=product_id, item=item, started_at=started_at,
        status=status, model_version=model_version, mapping_version=mapping_version,
        verdict=verdict, truth_label=truth_label, processed_at=processed_at))


def write_view(con, *, view_id, attempt_id, product_id, item, camera_id, image_uri,
               error_map_uri, status, model_version, mapping_version, width, height):
    con.execute(UPSERT_VIEW, dict(
        view_id=view_id, attempt_id=attempt_id, product_id=product_id, item=item,
        camera_id=camera_id, image_uri=image_uri, error_map_uri=error_map_uri,
        status=status, model_version=model_version, mapping_version=mapping_version,
        width=width, height=height))


def write_finding(con, *, finding_id, view_id, product_id, item, camera_id, kind,
                  bbox, score, part_id, model_version, mapping_version, map_uri, meta):
    con.execute(UPSERT_FINDING, dict(
        finding_id=finding_id, view_id=view_id, product_id=product_id, item=item,
        camera_id=camera_id,
        source="defect" if kind == "rtdetr_box" else "anomaly", kind=kind,
        x1=int(bbox[0]), y1=int(bbox[1]), x2=int(bbox[2]), y2=int(bbox[3]),
        score=float(score), part_id=part_id, model_version=model_version,
        mapping_version=mapping_version, map_uri=map_uri,
        meta_json=json.dumps(meta, ensure_ascii=False)))


# ---------------------------------------------------------------------------
# 추론 러너
# ---------------------------------------------------------------------------
ROIMapper = fusion.ROIMapper  # fusion.py이 단일 정의점


class FusionRunner:
    def __init__(self, args, cfg: dict):
        self.args = args
        self.cfg = cfg
        if not cfg.get("derived") or not cfg.get("score_norm"):
            raise ValueError("검증된 가중합 설정이 없습니다. 원본 Val로 derive_fusion.py를 먼저 실행하세요")
        import os
        os.environ.setdefault("DATABASE_URL", "sqlite:///" + str(Path(args.db).resolve()))
        migrate()
        self.db = dbconn.get_engine().connect()
        self.roi = fusion.ROIMapper(AGENT_ROOT / "config" / "parts_roi.json")
        ck_thr = fusion.load_hvq_thresholds(Path(args.hvq_checkpoint))
        self.hvq_thr, self.hvq_thr_source = fusion.merge_thresholds(
            ck_thr, AGENT_ROOT / "config" / "hvq_thresholds.json")
        log(f"[hvq] 임계값 출처: {self.hvq_thr_source}")
        self.bm = H.load_branch_mapping(Path(args.hvq_checkpoint))
        self.blur_min = float(cfg["capture"]["blur_laplacian_var_min"])
        self.expected = list(cfg["capture"]["expected_views"])
        self.save_verdicts = set(cfg["evidence"]["save_heatmap_for_verdicts"])
        self.heat_dir = AGENT_ROOT / cfg["evidence"]["heatmap_dir"]
        self.heat_dir.mkdir(parents=True, exist_ok=True)
        self.fail_log = open(AGENT_ROOT / "batch_failures.jsonl", "a", buffering=1)
        self._engines = None
        self.proc_times: list[float] = []
        self.t0 = time.time()

    # -- 엔진 지연 초기화
    def engines(self):
        if self._engines is None:
            import onnxruntime as ort  # noqa: PLC0415

            rt_cfg = self.cfg["rtdetr"]
            so_rt = ort.SessionOptions()
            so_rt.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            so_rt.intra_op_num_threads = int(self.cfg["runner"]["rtdetr_threads"])
            so_rt.inter_op_num_threads = 1
            rt = RTORTEngine(MV_ROOT / rt_cfg["onnx"],
                             shared.count_classes(shared.extract_state_dict(
                                 MV_ROOT / "epoch_0015.pt", use_ema=True)),
                             session_options=so_rt)
            hvq_cfg = self.cfg["hvq"]
            so_hv = ort.SessionOptions()
            so_hv.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            so_hv.intra_op_num_threads = int(self.cfg["runner"]["hvq_threads"])
            so_hv.inter_op_num_threads = 1
            hvq_path = MV_ROOT / (hvq_cfg["onnx_fp16"] if hvq_cfg["use_fp16"] else hvq_cfg["onnx_fp32"])
            hvq = H.HVQONNXFP16IOEngine(hvq_path, len(self.bm), session_options=so_hv) \
                if hvq_cfg["use_fp16"] else H.HVQONNXEngine(hvq_path, len(self.bm), session_options=so_hv)
            self._engines = (rt, hvq)
            self.hvq_model_version = (hvq_cfg["model_version_fp16"] if hvq_cfg["use_fp16"]
                                      else hvq_cfg["model_version_fp32"])
            self.rt_model_version = rt_cfg["model_version"]
        return self._engines

    # -- 흐림 검사
    @staticmethod
    def is_blurred(path: Path, threshold: float) -> bool:
        import cv2  # noqa: PLC0415

        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return True
        small = cv2.resize(img, (512, 512))
        return float(cv2.Laplacian(small, cv2.CV_64F).var()) < threshold

    def save_heatmap(self, product_id: str, cam: str, heat: np.ndarray) -> str:
        import cv2  # noqa: PLC0415

        h = heat.astype(np.float32)
        h = (h - h.min()) / (h.max() - h.min() + 1e-9)
        out = self.heat_dir / product_id
        out.mkdir(parents=True, exist_ok=True)
        p = out / f"{cam}_hvqmap.png"
        cv2.imwrite(str(p), (h * 255).astype(np.uint8))
        return str(p)

    # -- 뷰 배치 추론
    def infer_views(self, view_items: list[dict]) -> dict:
        """view_items: [{product, camera, path}]. 반환: {(pid,cam): 결과}."""
        import torch  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415

        rt, hvq = self.engines()
        pil = [Image.open(v["path"]).convert("RGB") for v in view_items]
        orig_sizes = torch.tensor([[im.width, im.height] for im in pil])
        rt_batch = shared.preprocess(pil, int(self.cfg["rtdetr"]["imgsz"]))
        hvq_batch = H.preprocess(pil, int(self.cfg["hvq"]["imgsz"]))
        labels = H.labels_for_images([v["path"] for v in view_items], self.bm,
                                     default=self.args.default_category)

        with torch.no_grad():
            logits, boxes = rt.infer(rt_batch)
        dets = shared.postprocess(logits, boxes, orig_sizes,
                                  conf=float(self.cfg["rtdetr"]["score_floor"]),
                                  iou=float(self.cfg["rtdetr"]["iou"]))
        hvq_pred = hvq.infer(hvq_batch, labels)
        hvq_scores_max16 = [float(x) for x in H.scores_from_pred(hvq_pred)]

        out = {}
        for v, det, hm, s16, im in zip(view_items, dets, hvq_pred, hvq_scores_max16, pil):
            boxes = [
                {"bbox": [float(b) for b in box], "score": float(sc), "label": int(lb),
                 "class_name": rt.class_names[int(lb)] if int(lb) < len(rt.class_names) else str(int(lb))}
                for box, sc, lb in zip(det["boxes"], det["scores"], det["labels"])
            ]
            out[(v["product"], v["camera"])] = {
                "rt_boxes": boxes,
                "rt_conf": max([b["score"] for b in boxes], default=0.0),
                "hvq_score": s16,
                "hvq_score_mean": float(H.scores_from_pred(hm.float().unsqueeze(0))[0]),
                "hvq_map": hm[0].float().cpu().numpy(),
                "width": im.width, "height": im.height,
            }
            im.close()
        return out

    # -- 제품 최종화(판정+기록)
    def finalize_product(self, product: dict, results: dict, started_at: str):
        pid = product["pid"]
        item = product["item"]
        truth = product["truth_label"]
        processed_at = datetime.now().isoformat(timespec="seconds")
        attempt_id = f"{pid}:{RUN_TAG}"

        all_rt = [b for cam in product["views"] for b in results[(pid, cam)]["rt_boxes"]]
        derived = fusion.load_derived()
        if derived is not None:
            rt_confs = [results[(pid, cam)]["rt_conf"] for cam in product["views"]]
            hvq_s = [results[(pid, cam)]["hvq_score"] for cam in product["views"]]
            dres = fusion.fuse_product_derived(rt_confs, hvq_s, derived)
            decision = {"verdict": dres["verdict"], "fusion_score": dres["fusion_score"],
                        "fusion_th": dres["th"], "fusion_margin": dres["margin"],
                        "agg": dres["agg"], "rt_positive": None, "hvq_positive": None,
                        "hvq_threshold": None}
        else:
            hvq_max = max(results[(pid, cam)]["hvq_score"] for cam in product["views"])
            thr = fusion.hvq_threshold(item, self.hvq_thr, float(self.cfg["hvq"]["threshold_default"]))
            decision = fusion.fuse_product(all_rt, hvq_max, thr,
                                           float(self.cfg["rtdetr"]["conf_threshold"]),
                                           self.cfg["fusion"])

        write_attempt(self.db, attempt_id=attempt_id, product_id=pid, item=item,
                      status="completed", verdict=decision["verdict"], truth_label=truth,
                      model_version=RUN_TAG, mapping_version=self.roi.version,
                      started_at=started_at, processed_at=processed_at)
        for cam, path in sorted(product["views"].items()):
            r = results[(pid, cam)]
            vid = f"{attempt_id}:{cam}"
            save_heat = decision["verdict"] in self.save_verdicts
            map_uri = self.save_heatmap(pid, cam, r["hvq_map"]) if save_heat else None
            write_view(self.db, view_id=vid, attempt_id=attempt_id, product_id=pid,
                       item=item, camera_id=cam, image_uri=path, error_map_uri=map_uri or "",
                       status="ok", model_version=RUN_TAG, mapping_version=self.roi.version,
                       width=r["width"], height=r["height"])
            hvq_meta = {"product_hvq_max": max(hvq_s) if derived is not None else r["hvq_score"],
                        "score_mean": r["hvq_score_mean"],
                        "score_variant": "max_avgpool16",
                        "threshold_source": self.hvq_thr_source}
            if derived is not None:
                hvq_meta.update({"fusion_score": decision["fusion_score"],
                                 "fusion_th": decision["fusion_th"],
                                 "fusion_margin": decision["fusion_margin"],
                                 "fusion_agg": decision["agg"]})
            write_finding(self.db,
                          finding_id=f"{vid}:hvq", view_id=vid, product_id=pid, item=item,
                          camera_id=cam, kind="hvq_score",
                          bbox=(0, 0, r["width"], r["height"]), score=r["hvq_score"],
                          part_id=self.roi.part_id(item, cam, (0, 0, r["width"], r["height"])),
                          model_version=self.hvq_model_version, mapping_version=self.roi.version,
                          map_uri=map_uri, meta=hvq_meta)
            rt_conf_floor = float(self.cfg["rtdetr"]["conf_threshold"])
            for i, b in enumerate([x for x in r["rt_boxes"] if x["score"] >= rt_conf_floor]):
                write_finding(self.db,
                              finding_id=f"{vid}:rt{i}", view_id=vid, product_id=pid, item=item,
                              camera_id=cam, kind="rtdetr_box", bbox=b["bbox"], score=b["score"],
                              part_id=self.roi.part_id(item, cam, b["bbox"]),
                              model_version=self.rt_model_version,
                              mapping_version=self.roi.version, map_uri=None,
                              meta={"class_name": b["class_name"]})
        self.db.commit()
        return decision

    def record_failure(self, product: dict, status: str, reason: str, started_at: str):
        pid = product["pid"]
        processed_at = datetime.now().isoformat(timespec="seconds")
        write_attempt(self.db, attempt_id=f"{pid}:{RUN_TAG}", product_id=pid,
                      item=product["item"], status=status, verdict=None,
                      truth_label=product["truth_label"], model_version=RUN_TAG,
                      mapping_version=self.roi.version, started_at=started_at,
                      processed_at=processed_at)
        self.db.commit()
        self.fail_log.write(json.dumps({
            "product_id": pid, "status": status, "reason": reason, "at": processed_at,
        }, ensure_ascii=False) + "\n")

    # -- 메인 루프
    def run(self, products: dict, done: set[str]):
        todo = [(pid, p) for pid, p in products.items() if pid not in done]
        if self.args.limit:
            todo = todo[: self.args.limit]
        total = len(todo)
        print(f"[batch] 대상 제품 {total}개 (완료 {len(done)}개 스킵)", flush=True)
        self.engines()  # 워밍업 겸 초기화

        batch_views = int(self.cfg["runner"]["batch_views"])
        every = int(self.cfg["runner"]["progress_every"])
        buffer: list[dict] = []
        pending: dict[str, dict] = {}
        state = {"processed": 0, "failed": 0}
        t_start = time.time()

        def flush():
            nonlocal buffer
            if not buffer:
                return
            try:
                results = self.infer_views(buffer)
            except Exception as e:  # noqa: BLE001
                for v in buffer:
                    prod = v["product_ref"]
                    if prod["pid"] not in pending:
                        self.record_failure(prod, "inference_error",
                                            f"{type(e).__name__}: {e}", prod["started_at"])
                        state["failed"] += 1
                        state["processed"] += 1
                buffer = []
                return
            for v in buffer:
                pid = v["product"]
                pending.setdefault(pid, {})[(pid, v["camera"])] = results[(pid, v["camera"])]
                prod = v["product_ref"]
                prod["remaining"].discard(v["camera"])
                if not prod["remaining"]:
                    self._complete(prod, pending.pop(pid), started_at=prod["started_at"])
                    state["processed"] += 1
            buffer = []

        for idx, (pid, p) in enumerate(todo, 1):
            started_at = datetime.now().isoformat(timespec="seconds")
            prod = {"pid": pid, "item": p["item"], "truth_label": p["truth_label"],
                    "views": p["views"], "started_at": started_at,
                    "remaining": set(p["views"].keys())}
            missing = [c for c in self.expected if c not in p["views"]]
            if missing:
                self.record_failure(prod, "capture_missing", f"누락 시점: {missing}", started_at)
                state["failed"] += 1
                state["processed"] += 1
                continue
            try:
                for cam, path in sorted(p["views"].items()):
                    if self.is_blurred(Path(path), self.blur_min):
                        raise ValueError(f"흐림 감지: {cam}")
                    buffer.append({"product": pid, "camera": cam, "path": path,
                                   "product_ref": prod})
                if len(buffer) >= batch_views:
                    flush()
            except ValueError as e:
                self.record_failure(prod, "capture_blurred", str(e), started_at)
                state["failed"] += 1
                state["processed"] += 1
                continue
            except KeyboardInterrupt:
                flush()
                raise
            except Exception as e:  # noqa: BLE001
                self.record_failure(prod, "inference_error", f"{type(e).__name__}: {e}", started_at)
                state["failed"] += 1
                state["processed"] += 1
                continue
            if idx % every == 0:
                flush()
                el = time.time() - t_start
                rate = state["processed"] / el if el > 0 else 0
                eta = (total - state["processed"]) / rate if rate > 0 else 0
                print(f"[batch] {state['processed']}/{total} (실패 {state['failed']}) "
                      f"{rate:.2f} prod/s, ETA {eta/60:.1f}분, "
                      f"경과 {el/60:.1f}분", flush=True)
        flush()
        self._report(final=True)

    def _complete(self, prod, results, started_at: str):
        t0 = time.perf_counter()
        decision = self.finalize_product(prod, results, started_at)
        self.proc_times.append(time.perf_counter() - t0)
        self.last_decision = decision

    def _report(self, final: bool = False):
        import numpy as np  # noqa: PLC0415

        if self.proc_times:
            arr = np.array(self.proc_times) * 1000
            print(f"[batch] 제품당 기록 p50={np.percentile(arr,50):.0f}ms "
                  f"p95={np.percentile(arr,95):.0f}ms (n={len(arr)})", flush=True)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="퓨전 배치 러너")
    p.add_argument("--dataset", default=str(MV_ROOT / "dataset"))
    p.add_argument("--db", default=str(AGENT_ROOT / "inspection.db"))
    p.add_argument("--config", default=str(AGENT_ROOT / "config" / "fusion.json"))
    p.add_argument("--hvq-checkpoint", default=str(MV_ROOT / "hvq_best.pt"))
    p.add_argument("--limit", type=int, default=None, help="처리할 제품 수(파일럿)")
    p.add_argument("--default-category", default=None)
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    cfg = fusion.load_config(Path(args.config))
    products, stats = scan_dataset(Path(args.dataset))
    print(f"[scan] 파일 {stats['files']}장, 파싱 불가 {stats['unparsed']}, "
          f"제품 {len(products)}개 (뷰 {stats['views']}장)", flush=True)

    runner = FusionRunner(args, cfg)
    done = load_done(RUN_TAG)
    try:
        runner.run(products, done)
    except KeyboardInterrupt:
        print("\n[batch] 중단됨 — 재실행 시 완료 제품은 스킵하고 이어서 처리합니다.", flush=True)
        return 130
    finally:
        runner.fail_log.close()
        runner.db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
