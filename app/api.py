"""GUI와 LLM 에이전트가 공통으로 쓰는 도구 API."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError, Field

from .db import configure
from .tools import TOOL_FUNCS, TOOL_SCHEMAS, DEFINITION_VERSION, ToolError, ReviewConflict

logger = logging.getLogger("inspection.api")
logging.basicConfig(level=logging.INFO)


class ExtractIn(BaseModel):
    product_id: str
    camera_id: str
    source: str = "anomaly"
    threshold_mode: str = "p99"
    min_area_px: int = 24
    threshold_value: float | None = None


class MetricsIn(BaseModel):
    item: str
    part_id: str | None = None
    camera_id: str | None = None
    date_from: str
    date_to: str
    model_version: str
    review_state: str = "confirmed"


class StatsIn(BaseModel):
    item: str
    metric: str
    group_by: list[str]
    date_from: str | None = None
    date_to: str | None = None
    model_version: str | None = None
    min_denominator: int = 1
    order: str = "desc"
    limit: int = 10


class EvidenceIn(BaseModel):
    stat_key: str | None = None
    product_id: str | None = None
    part_id: str | None = None
    camera_id: str | None = None
    limit: int = 20


INPUT_MODELS = {
    "extract_abnormal_locations": ExtractIn,
    "compute_inspection_metrics": MetricsIn,
    "query_error_stats": StatsIn,
    "get_case_evidence": EvidenceIn,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    from . import db as _db

    configure(os.getenv("DATABASE_URL", None))
    from migrate import migrate
    migrate()
    _db.get_engine("read")
    _db.get_engine("review")
    logger.info("[api] backend=%s (DATABASE_URL 미설정 시 SQLite 폐백)",
                _db.backend_name())
    from .recompute import start_worker

    start_worker()
    yield


app = FastAPI(title="manufacturing-inspection-tools", lifespan=lifespan)
from .part_api import router as part_heatmap_router
app.include_router(part_heatmap_router)
from .shared_data_api import router as shared_data_router
app.include_router(shared_data_router)
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
_web=json.loads((Path(__file__).resolve().parents[1]/"config/web.json").read_text())
app.add_middleware(CORSMiddleware,allow_origins=_web["allowed_origins"],allow_methods=["GET","POST"],allow_headers=["Content-Type"])



def _error_response(status: int, tool: str, body, message: str) -> JSONResponse:
    summary = str(body)
    if len(summary) > 300:
        summary = summary[:300] + "…"
    return JSONResponse(
        status_code=status,
        content={"error": {"tool": tool, "input_summary": summary, "message": message}},
    )


def _llm_mode() -> dict:
    import os  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415

    if os.getenv("AGENT_MOCK", "") == "1":
        return {"mode": "mock", "model": None}
    try:
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").replace("/v1", "")
        with urllib.request.urlopen(f"{base}/api/tags", timeout=2) as r:
            return {"mode": "real" if r.status == 200 else "mock",
                    "model": os.getenv("OLLAMA_MODEL", "qwen25-cpu")}
    except Exception:  # noqa: BLE001
        return {"mode": "mock", "model": None}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "inspection-tools",
        "definition_version": DEFINITION_VERSION,
        "model_version": None,
        "mapping_version": None,
        "llm": _llm_mode(),
    }


@app.get("/tools")
def list_tools():
    return {
        "tools": sorted(TOOL_FUNCS),
        "schemas": TOOL_SCHEMAS,
        "definition_version": DEFINITION_VERSION,
        "model_version": None,
        "mapping_version": None,
    }


@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        return _error_response(400, tool_name, "(invalid json body)", "요청 본문이 올바른 JSON이 아닙니다")
    try:
        input_model = INPUT_MODELS.get(tool_name)
        if input_model is None:
            return _error_response(404, tool_name, body, f"알 수 없는 도구입니다: {tool_name}")
        try:
            kwargs = input_model(**body).model_dump()
        except ValidationError:
            return _error_response(400, tool_name, body, "입력값 형식이 올바르지 않습니다")
        return TOOL_FUNCS[tool_name](**kwargs)
    except ReviewConflict as e:
        return _error_response(409, tool_name, body, str(e))
    except ToolError as e:
        return _error_response(400, tool_name, body, str(e))
    except Exception:
        logger.exception("tool %s failed, input=%s", tool_name, body)
        return _error_response(500, tool_name, body, '내부 오류가 발생했습니다. 잠시 후 다시 시도하세요.')


class RequestReviewIn(BaseModel):
    product_id: str
    reason: str
    part_id: str | None = None
    camera_id: str | None = None
    reviewer: str = "agent"


class TrainingStatusIn(BaseModel):
    item: str | None = None


INPUT_MODELS["request_review"] = RequestReviewIn
INPUT_MODELS["get_training_status"] = TrainingStatusIn
INPUT_MODELS["get_final_performance"] = TrainingStatusIn
class SpatialEvidenceIn(BaseModel):
    item:str
    product_id:str|None=None
    camera:Literal['C1','C2','C3','C4','C5']='C1'
    region_id:str|None=None
    model:Literal['rt','hvq']='rt'
    method:str|None=None
    resolution:Literal[16,32,64,128]=64
    limit:int=Field(default=5,ge=1,le=20)
INPUT_MODELS['query_spatial_evidence']=SpatialEvidenceIn


class SubmitReviewIn(BaseModel):
    product_id: str
    camera_id: str
    bbox: list[float]
    truth_label: str
    fp_fn: str | None = None
    reviewer: str = "gui"
    reason: str | None = None
    expected_version: int | None = None


INPUT_MODELS["submit_review"] = SubmitReviewIn


class ChatIn(BaseModel):
    question: str


@app.post("/chat")
async def chat_endpoint(body: ChatIn):
    """GUI 챗봇 패널용. LLM 에이전트(agent.py)를 호출한다."""
    try:
        import agent as agent_mod  # noqa: PLC0415

        from starlette.concurrency import run_in_threadpool
        answer = await run_in_threadpool(agent_mod.chat, body.question)
        return {"answer": answer, "mode": agent_mod.MODE}
    except Exception:  # noqa: BLE001
        logger.exception("chat failed")
        return JSONResponse(status_code=500, content={
            "error": {"tool": "chat", "input_summary": body.question[:120],
                      "message": "챗봇 호출에 실패했습니다 (Ollama 상태를 확인하세요)"}})


@app.get("/metrics/snapshots")
def snapshot_list(baseline_kind: str | None = None):
    from .db import get_session
    from .models import MetricsSnapshot
    from sqlalchemy import select
    with get_session("read") as session:
        query=select(MetricsSnapshot)
        if baseline_kind:query=query.where(MetricsSnapshot.baseline_kind==baseline_kind)
        rows=session.scalars(query.order_by(MetricsSnapshot.snapshot_id.desc()).limit(500)).all()
        return {"rows":[{col.name:getattr(r,col.name) for col in MetricsSnapshot.__table__.columns} for r in rows]}


@app.get("/evidence/{view_id}/image")
def evidence_image(view_id: str):
    from .models import View
    from .db import get_session
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from pathlib import Path
    import json
    with get_session("read") as session:
        view=session.get(View,view_id)
        if view is None:raise HTTPException(404,"시점 없음")
        path=Path(view.image_uri).resolve()
    cfg=json.loads((Path(__file__).resolve().parents[1]/"config/evidence_roots.json").read_text())
    if not any(path.is_relative_to(Path(p).resolve()) for p in cfg["allowed_roots"]):
        raise HTTPException(403,"허용된 근거 루트 밖의 경로")
    if not path.is_file():raise HTTPException(404,"원본 이미지 없음")
    return FileResponse(path)


@app.get("/evidence/{view_id}/map")
def evidence_map(view_id: str):
    """표시용 overlay만 생성한다. 원시 score/판정값은 변경하지 않는다."""
    from .models import View
    from .db import get_session
    from fastapi import HTTPException,Response
    import numpy as np
    import cv2
    with get_session("read") as session:
        view=session.get(View,view_id)
        if view is None or not view.error_map_uri:raise HTTPException(404,"저장된 raw map 없음")
        source=Path(view.image_uri).resolve();raw=Path(view.error_map_uri).resolve()
    cfg=json.loads((Path(__file__).resolve().parents[1]/"config/evidence_roots.json").read_text())
    if not any(raw.is_relative_to(Path(p).resolve()) for p in cfg["allowed_map_roots"]):raise HTTPException(403,"허용된 맵 루트 밖")
    if not any(source.is_relative_to(Path(p).resolve()) for p in cfg["allowed_roots"]):raise HTTPException(403,"허용된 이미지 루트 밖")
    if not raw.is_file() or not source.is_file():raise HTTPException(404,"원본/맵 없음")
    values=np.load(raw,allow_pickle=False).squeeze();image=cv2.imread(str(source))
    if values.ndim!=2 or not np.isfinite(values).all() or image is None:raise HTTPException(422,"유효하지 않은 원본/맵")
    display=cfg["map_display"];lo,hi=np.percentile(values,[display["lower_percentile"],display["upper_percentile"]])
    scaled=np.zeros_like(values,dtype=np.uint8) if hi<=lo else (np.clip((values-lo)/(hi-lo),0,1)*255).astype(np.uint8)
    color=cv2.applyColorMap(cv2.resize(scaled,(image.shape[1],image.shape[0])),cv2.COLORMAP_JET)
    alpha=display['heat_alpha'];overlay=cv2.addWeighted(image,1-alpha,color,alpha,0)
    ok,data=cv2.imencode('.png',overlay)
    if not ok:raise HTTPException(500,"맵 표시 생성 실패")
    return Response(data.tobytes(),media_type='image/png',headers={'X-Map-Scaling':'PER_VIEW_PERCENTILES_VISUALIZATION_ONLY'})


# ---------------------------------------------------------------- 인트로 위젯/성능

@app.get("/status/overview")
def status_overview():
    from . import status
    return status.overview()


@app.get("/performance/final")
def performance_final():
    from . import status
    payload = status.final_performance_payload()
    summary = status.final_performance_summary(payload)
    summary["state"] = status.final_performance_state(payload=payload)
    return {
        "available": payload["available"],
        "is_fixture": payload["is_fixture"],
        "state": summary["state"],
        "report_path": payload["report_path"],
        "summary": summary,
        "report": payload["report"],
    }


@app.get("/fusion/runs")
def fusion_runs():
    """기록된 퓨전 run 목록 — 활성 run이 첫 번째 (대시보드 '모델 기준선' 필터용)."""
    from sqlalchemy import text
    from .db import get_engine
    engine = get_engine("read")
    try:
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT fusion_run_id, status, is_active, deployment_eligible, "
                "       profile, metadata, created_at "
                "FROM fusion_analysis.model_runs ORDER BY is_active DESC, created_at DESC"
            )).mappings().all()
    except Exception:  # noqa: BLE001
        return {"runs": []}
    runs = []
    for row in rows:
        profile = row.get("profile") or {}
        metadata = row.get("metadata") or {}
        runs.append({
            "fusion_run_id": row["fusion_run_id"],
            "status": row["status"],
            "is_active": bool(row["is_active"]),
            "deployment_eligible": bool(row["deployment_eligible"]),
            "contract_version": profile.get("contract_version"),
            "normalization": profile.get("normalization"),
            "hvq_score_variant": profile.get("hvq_score_variant"),
            "report_model_version": metadata.get("report_model_version"),
            "evaluation_products": metadata.get("evaluation_products"),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        })
    return {"runs": runs}


# ---------------------------------------------------------------- GUI 추론

@app.get("/items")
def items_list():
    from .gui_inference import list_items
    return {"items": list_items()}


@app.get("/inference/sample_products")
def inference_sample_products(item: str, limit: int = 8):
    from .gui_inference import sample_products
    return {"item": item, "products": sample_products(item, max(1, min(limit, 50)))}


class InferenceRunIn(BaseModel):
    item: str | None = None
    mode: str = "upload"  # upload | existing
    product_id: str | None = None
    record: bool = True


@app.post("/inference/run")
async def inference_run(request: Request):
    """5시점 GUI 추론. multipart: item, mode, [C1..C5 파일 | product_id]."""
    from starlette.concurrency import run_in_threadpool
    from . import gui_inference

    try:
        form = await request.form()
    except Exception:
        logger.exception("inference_run form parse failed")
        return _error_response(400, "inference_run", "(invalid form)", "multipart 폼을 파싱하지 못했습니다")

    item = str(form.get("item") or "").strip()
    mode = str(form.get("mode") or "upload")
    product_id = str(form.get("product_id") or "").strip() or None
    record = str(form.get("record", "1")) != "0"
    if not item:
        return _error_response(400, "inference_run", dict(form), "item이 필요합니다")

    valid_items = await run_in_threadpool(gui_inference.list_items)
    if item not in valid_items:
        return _error_response(400, "inference_run", {"item": item},
                               f"알 수 없는 품목입니다(로드된 품목 {len(valid_items)}개 중 없음)")

    try:
        if mode == "existing":
            if not product_id:
                return _error_response(400, "inference_run", {"mode": mode},
                                       "existing 모드는 product_id가 필요합니다")
            views = await run_in_threadpool(gui_inference.product_view_paths, product_id)
            result = await run_in_threadpool(
                gui_inference.run_gui_inference, item=item, views=views,
                product_id=product_id, record=record)
        else:
            from starlette.datastructures import UploadFile
            import shutil
            upload_dir = gui_inference.GUI_EVIDENCE_ROOT / "uploads" / uuid4().hex[:12]
            views: dict = {}
            for cam in ("C1", "C2", "C3", "C4", "C5"):
                f = form.get(cam)
                if not isinstance(f, UploadFile):
                    return _error_response(400, "inference_run", {"missing": cam},
                                           f"{cam} 업로드 파일이 필요합니다")
                suffix = Path(f.filename or "").suffix.lower() or ".jpg"
                if suffix not in {".jpg", ".jpeg", ".png"}:
                    return _error_response(400, "inference_run", {"cam": cam, "name": f.filename},
                                           "jpg/jpeg/png 이미지만 허용합니다")
                upload_dir.mkdir(parents=True, exist_ok=True)
                dest = upload_dir / f"{cam}{suffix}"
                with dest.open("wb") as out:
                    shutil.copyfileobj(f.file, out)
                views[cam] = dest
            result = await run_in_threadpool(
                gui_inference.run_gui_inference, item=item, views=views,
                product_id=product_id, record=record)
        return result
    except (ValueError, FileNotFoundError) as e:
        return _error_response(400, "inference_run",
                               {"item": item, "mode": mode, "product_id": product_id}, str(e))
    except Exception as e:  # noqa: BLE001
        logger.exception("inference_run failed")
        return _error_response(500, "inference_run",
                               {"item": item, "mode": mode, "product_id": product_id},
                               f"추론 실행 실패: {e}")
