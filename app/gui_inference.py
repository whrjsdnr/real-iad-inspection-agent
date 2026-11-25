"""GUI 5시점 추론 오케스트레이션.

MV 추론 venv 서브프로세스(scripts/gui_infer_runner.py)로 두 모델을 실행하고,
결과를 DB에 source='gui' 계열로 기록한다 (배치 데이터와 지표 집계 분리:
모든 model_version에 'gui-fusion-v1' 태그, findings.source='gui').

퓨전 계약(가중치/임계/백분위 lookup/TH·margin)은 DB model_runs(읽기 전용)에서
확정값을 읽는다 — 백그라운드 파이프라인과 동일한 계약을 쓴다.
"""
from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from .db import get_engine, get_session
from .gui_fusion import verdict_rationale
from .rois import MAPPING_VERSION, map_bbox_to_part

AGENT_ROOT = Path(__file__).resolve().parents[1]
GUI_EVIDENCE_ROOT = Path(os.getenv("GUI_EVIDENCE_ROOT", str(AGENT_ROOT / "gui_evidence")))
MV_PYTHON = os.getenv("GUI_MV_PYTHON", "/home/geonug/MV/inference/.venv/bin/python")
RUNNER = AGENT_ROOT / "scripts" / "gui_infer_runner.py"
MV_ROOT = Path(os.getenv("GUI_MV_ROOT", "/home/geonug/MV"))

GUI_MODEL_TAG = "gui-fusion-v1"


def _fusion_config() -> dict:
    return json.loads((AGENT_ROOT / "config" / "fusion.json").read_text())


def load_fusion_contract(item: str) -> dict:
    """백그라운드 파이프라인과 동일한 퓨전 계약을 읽는다 (DB 우선, 설정 폐백)."""
    cfg = _fusion_config()
    contract = {
        "rtdetr": {
            "onnx": cfg["rtdetr"]["onnx"],
            "imgsz": cfg["rtdetr"]["imgsz"],
            "score_floor": cfg["rtdetr"].get("score_floor", 0.05),
            "iou": cfg["rtdetr"]["iou"],
        },
        "hvq": {
            "onnx_fp16": cfg["hvq"]["onnx_fp16"],
            "imgsz": cfg["hvq"]["imgsz"],
        },
        "weights": dict(cfg["weights"]),
        "hvq_threshold": float(cfg["hvq"].get("threshold_default", 81.0)),
        "rtdetr_conf_threshold": 0.55,
        "category_params": None,
    }
    engine = get_engine("read")
    try:
        with engine.connect() as c:
            run = c.execute(text(
                "SELECT profile, parameters FROM fusion_analysis.model_runs "
                "WHERE parameters IS NOT NULL ORDER BY is_active DESC LIMIT 1"
            )).mappings().first()
    except Exception:  # noqa: BLE001
        run = None
    if run:
        profile = run.get("profile") or {}
        params = run.get("parameters") or {}
        contract["rtdetr_conf_threshold"] = float(
            profile.get("rtdetr_conf_threshold", contract["rtdetr_conf_threshold"]))
        weights = profile.get("weights")
        if weights:
            contract["weights"] = {"rtdetr": float(weights["rtdetr"]),
                                   "hvq": float(weights["hvq"])}
        if profile.get("contract_version"):
            contract["contract_version"] = profile["contract_version"]
        hvq_thresholds = profile.get("hvq_thresholds") or {}
        if item in hvq_thresholds:
            contract["hvq_threshold"] = float(hvq_thresholds[item])
        cat = (params.get("categories") or {}).get(item)
        if cat and cat.get("status") == "CONFIGURED":
            contract["category_params"] = cat
    return contract


def prepare_job(*, item: str, views: dict[str, Path], product_id: str | None,
                attempt_id: str) -> Path:
    cfg = _fusion_config()
    contract = load_fusion_contract(item)
    job = {
        "item": item,
        "product_id": product_id,
        "views": {cam: str(views[cam]) for cam in sorted(views)},
        "out_dir": str(GUI_EVIDENCE_ROOT / attempt_id),
        "contract": contract,
        "rtdetr_checkpoint": str(MV_ROOT / "epoch_0015.pt"),
        "hvq_checkpoint": str(MV_ROOT / "hvq_best.pt"),
        "model_versions": cfg.get("model_versions", {}),
        "config_version": cfg.get("version"),
    }
    job_dir = GUI_EVIDENCE_ROOT / attempt_id
    job_dir.mkdir(parents=True, exist_ok=True)
    job_path = job_dir / "job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2))
    return job_path


def run_inference_subprocess(job_path: Path, timeout: float | None = None) -> dict:
    timeout = timeout or float(os.getenv("GUI_INFER_TIMEOUT", "300"))
    result_path = job_path.with_name("result.json")
    proc = subprocess.run(
        [MV_PYTHON, str(RUNNER), "--job", str(job_path),
         "--result", str(result_path)],
        cwd=str(MV_ROOT), capture_output=True, text=True, timeout=timeout,
    )
    if not result_path.is_file():
        raise RuntimeError(
            f"추론 러너가 결과를 만들지 못했습니다 "
            f"(rc={proc.returncode}): {proc.stderr[-500:]}")
    result = json.loads(result_path.read_text())
    if not result.get("ok"):
        raise RuntimeError(f"추론 실패: {result.get('error')}")
    return result


def record_result(result: dict, *, attempt_id: str, product_id: str,
                  item: str) -> dict:
    """GUI 추론 결과를 DB에 기록한다 — attempt + 5 views + findings(source='gui')."""
    from .models import Attempt, Finding, View

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    cfg = _fusion_config()
    model_tag = GUI_MODEL_TAG
    # GUI 기록은 attempt+view+finding 일괄 삽입이 필요한데, app_review는 reviews만 갱신 가능하고
    # app_workflow는 inspection_views 권한이 없다. 스키마/권한 변경 없이 배치가 쓰는
    # admin 연결(기존 설정 DATABASE_URL)로 기록한다 — 모델 버전 'gui-fusion-v1' 태그로
    # 배치 데이터와 지표 집계가 분리된다.
    with get_session() as s:
        s.add(Attempt(
            attempt_id=attempt_id, product_id=product_id, item=item,
            started_at=now, status="completed", model_version=model_tag,
            mapping_version=MAPPING_VERSION,
            verdict=result["product"].get("verdict"),
            review_status=None, truth_label=None, processed_at=now,
        ))
        for cam, v in sorted(result["views"].items()):
            view_id = f"{attempt_id}:{cam}"
            s.add(View(
                view_id=view_id, attempt_id=attempt_id, product_id=product_id,
                item=item, camera_id=cam,
                image_uri=v["image_path"], error_map_uri=v["map_npy"],
                width=v["width"], height=v["height"], status="ok",
                model_version=model_tag, mapping_version=MAPPING_VERSION,
            ))
            for i, d in enumerate(v["detections"][:50]):
                x1, y1, x2, y2 = (int(round(float(x))) for x in d["bbox"])
                part_id = map_bbox_to_part(item, cam, (x1, y1, x2, y2))
                s.add(Finding(
                    finding_id=f"{view_id}-G{i + 1:02d}", view_id=view_id,
                    product_id=product_id, item=item, camera_id=cam,
                    source="gui", kind="rtdetr_box",
                    bbox_x1=x1, bbox_y1=y1, bbox_x2=x2, bbox_y2=y2,
                    score=float(d["score"]), part_id=part_id,
                    model_version=cfg.get("model_versions", {}).get("rtdetr", model_tag),
                    mapping_version=MAPPING_VERSION,
                    meta_json=json.dumps({"class_id": d["class_id"],
                                          "class_name": d["class_name"]},
                                         ensure_ascii=False),
                ))
        s.commit()
    return {"attempt_id": attempt_id, "product_id": product_id,
            "model_version": model_tag, "recorded": True}


def run_gui_inference(*, item: str, views: dict[str, Path],
                      product_id: str | None = None,
                      record: bool = True) -> dict:
    """전체 흐름: job 준비 → 서브프로세스 추론 → DB 기록 → 결과 반환."""
    attempt_id = f"gui-{uuid.uuid4().hex[:12]}"
    if product_id is None:
        product_id = f"gui_{item}_{uuid.uuid4().hex[:8]}"
    job_path = prepare_job(item=item, views=views, product_id=product_id,
                           attempt_id=attempt_id)
    result = run_inference_subprocess(job_path)
    result["rationale"] = verdict_rationale(result["product"])
    if record:
        result["db_record"] = record_result(
            result, attempt_id=attempt_id, product_id=product_id, item=item)
    else:
        result["db_record"] = {"recorded": False}
    return result


def sample_products(item: str, limit: int = 8) -> list[str]:
    """해당 품목의 검사 완료 제품 중 5시점 이미지가 모두 있는 것들."""
    engine = get_engine("read")
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT a.product_id
            FROM inspection_attempts a
            WHERE a.item = :item AND a.status = 'completed'
              AND (SELECT count(*) FROM inspection_views v
                   WHERE v.attempt_id = a.attempt_id AND v.status = 'ok') = 5
            ORDER BY a.product_id
            LIMIT :limit
        """), {"item": item, "limit": limit}).all()
    return [r[0] for r in rows]


def product_view_paths(product_id: str) -> dict[str, Path]:
    """기존 제품의 C1~C5 원본 이미지 경로."""
    engine = get_engine("read")
    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT camera_id, image_uri FROM inspection_views v "
            "JOIN inspection_attempts a USING(attempt_id) "
            "WHERE a.product_id = :p AND v.status = 'ok' "
            "ORDER BY v.camera_id"
        ), {"p": product_id}).all()
    views = {cam: Path(uri) for cam, uri in rows}
    if sorted(views) != ["C1", "C2", "C3", "C4", "C5"]:
        raise ValueError(f"제품의 5시점 이미지가 불완전합니다: {sorted(views)}")
    for cam, p in views.items():
        if not p.is_file():
            raise FileNotFoundError(f"{cam} 원본 이미지 없음: {p}")
    return views


def list_items() -> list[str]:
    engine = get_engine("read")
    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT item, count(*) AS n FROM inspection_attempts "
            "GROUP BY item ORDER BY item")).all()
    return [r[0] for r in rows]
