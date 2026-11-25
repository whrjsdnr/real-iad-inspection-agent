"""GUI/LLM 에이전트가 공통으로 쓰는 검증된 도구 4개.

LLM은 SQL을 직접 만들지 않고 이 도구만 호출한다.
모든 응답은 model_version, mapping_version, definition_version을 포함한다.
"""
from __future__ import annotations

import json
from contextlib import contextmanager

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm.exc import StaleDataError

from .db import get_session
from .models import Attempt, Finding, Review, User, View
from .providers.mock import get_provider
from .rois import map_bbox_to_part

DEFINITION_VERSION = "metrics-v1"

CONFIRMED_DEFECT_RATE = "confirmed_defect_rate"
PART_MISS_RATE = "part_miss_rate"
PART_FALSE_ALARM_RATE = "part_false_alarm_rate"
CAPTURE_PROCESS_FAILURE_RATE = "capture_process_failure_rate"
REVIEW_BASED_METRICS = (CONFIRMED_DEFECT_RATE, PART_MISS_RATE, PART_FALSE_ALARM_RATE)
ALL_METRICS = REVIEW_BASED_METRICS + (CAPTURE_PROCESS_FAILURE_RATE,)

# 누락·흐림·추론 오류
FAIL_STATUSES = {"capture_missing", "capture_blurred", "inference_error"}
GROUPABLE = {"part_id", "camera_id", "model_version"}


class ToolError(ValueError):
    """사용자에게 안전하게 보여줄 수 있는 입력/도메인 오류."""


class ReviewConflict(ToolError):
    """The client must reload the review before retrying."""


@contextmanager
def _session(session=None, role: str = "admin"):
    if session is not None:
        yield session
        return
    s = get_session(role)
    try:
        yield s
        s.commit()
    except StaleDataError as e:
        s.rollback()
        raise ReviewConflict("검수 버전 충돌: 새로고침 후 다시 시도하세요") from e
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


# ---------------------------------------------------------------- 조회 헬퍼

def _resolve_fusion_run(session, model_version):
    """대시보드 '모델 기준선'의 fusion run id를 근거 레이어로 해석한다.

    fusion_analysis run 판정은 동일 저장 점수의 재해석이며 근거
    (attempts/findings)는 run 간 동일하므로, run id 선택은 전체 근거 집계와
    동일하게 처리한다. run id가 아니면 원래 값을 그대로 쓴다.
    """
    if not model_version:
        return model_version
    try:
        from sqlalchemy import text
        row = session.execute(text(
            "SELECT 1 FROM fusion_analysis.model_runs WHERE fusion_run_id=:m"),
            {"m": model_version}).first()
    except Exception:  # noqa: BLE001
        return model_version
    return None if row else model_version


def _fetch_reviews(session, *, item, part_id, camera_id, date_from, date_to, review_state):
    q = select(Review).where(Review.item == item, Review.review_state == review_state)
    if part_id:
        q = q.where(Review.part_id == part_id)
    if camera_id:
        q = q.where(Review.camera_id == camera_id)
    if date_from:
        q = q.where(Review.reviewed_at >= date_from)
    if date_to:
        q = q.where(Review.reviewed_at <= date_to)
    return list(session.scalars(q).all())


def _fetch_attempts(session, *, item, model_version, date_from, date_to):
    q = select(Attempt).where(Attempt.item == item)
    if model_version:
        q = q.where(Attempt.model_version == model_version)
    if date_from:
        q = q.where(Attempt.started_at >= date_from)
    if date_to:
        q = q.where(Attempt.started_at <= date_to)
    return list(session.scalars(q).all())


def _predicted_keys(session, *, item, part_id, camera_id, model_version):
    """(product_id, part_id, camera_id) 중 model_version의 finding이 있는 쌍."""
    q = select(Finding.product_id, Finding.part_id, Finding.camera_id).where(Finding.item == item)
    if model_version:
        q = q.where(Finding.model_version == model_version)
    if part_id:
        q = q.where(Finding.part_id == part_id)
    if camera_id:
        q = q.where(Finding.camera_id == camera_id)
    return {tuple(row) for row in session.execute(q).all()}


def _rate(num: int, den: int) -> dict:
    if den == 0:
        return {"num": num, "den": den, "rate": None, "reason": "denominator_zero"}
    return {"num": num, "den": den, "rate": round(num / den, 6), "reason": None}


def _check_review_state(review_state: str) -> None:
    if review_state not in ("pending", "confirmed"):
        raise ToolError(f"review_state는 pending 또는 confirmed여야 합니다: {review_state}")


# ---------------------------------------------------------------- 도구 1

def _components_from_error_map(error_map, threshold_mode, min_area_px, fixed_value, provider):
    if threshold_mode == "p95":
        thr = float(np.percentile(error_map, 95))
    elif threshold_mode == "p99":
        thr = float(np.percentile(error_map, 99))
    else:  # fixed
        thr = float(fixed_value if fixed_value is not None else provider.fixed_threshold)
    mask = (error_map >= thr).astype(np.uint8)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    n, labels, stats, cents = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out = []
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area_px:
            continue
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        bw = int(stats[i, cv2.CC_STAT_WIDTH])
        bh = int(stats[i, cv2.CC_STAT_HEIGHT])
        score = round(float(error_map[labels == i].mean()), 4)
        out.append(
            {
                "bbox": (x, y, x + bw, y + bh),
                "centroid": (round(float(cents[i][0]), 1), round(float(cents[i][1]), 1)),
                "area_px": area,
                "score": score,
            }
        )
    out.sort(key=lambda r: (-r["score"], r["bbox"]))
    return out


def extract_abnormal_locations(
    *,
    product_id: str,
    camera_id: str,
    source: str = "anomaly",
    threshold_mode: str = "p99",
    min_area_px: int = 24,
    threshold_value: float | None = None,
    session=None,
) -> dict:
    """mock 오차 맵에서 임계값+형태학+connected components로 이상 영역을 추출하고
    ROI LUT으로 part_id를 매핑해 findings에 저장한다."""
    if source not in ("anomaly", "defect"):
        raise ToolError(f"source는 anomaly 또는 defect여야 합니다: {source}")
    if threshold_mode not in ("p95", "p99", "fixed"):
        raise ToolError(f"threshold_mode는 p95/p99/fixed여야 합니다: {threshold_mode}")
    if min_area_px < 1:
        raise ToolError("min_area_px는 1 이상이어야 합니다")

    with _session(session, role="review") as s:
        view = s.scalar(
            select(View).where(View.product_id == product_id, View.camera_id == camera_id)
        )
        if view is None:
            raise ToolError(f"검사 뷰를 찾을 수 없습니다: product_id={product_id}, camera_id={camera_id}")

        provider = get_provider(source)
        if source == "anomaly":
            error_map = provider.error_map(product_id, camera_id)
            raw = _components_from_error_map(
                error_map, threshold_mode, min_area_px,
                threshold_value if threshold_mode == "fixed" else None, provider,
            )
        else:
            raw = []
            for det in provider.detect(product_id, camera_id):
                x1, y1, x2, y2 = det.bbox
                if (x2 - x1) * (y2 - y1) >= min_area_px:
                    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                    raw.append(
                        {
                            "bbox": det.bbox,
                            "centroid": (round(cx, 1), round(cy, 1)),
                            "area_px": int((x2 - x1) * (y2 - y1)),
                            "score": round(float(det.score), 4),
                        }
                    )
            raw.sort(key=lambda r: (-r["score"], r["bbox"]))

        existing = len(
            s.scalars(select(Finding).where(Finding.view_id == view.view_id)).all()
        )
        regions = []
        for i, r in enumerate(raw):
            part_id = map_bbox_to_part(
                view.item, camera_id, r["bbox"], mapping_version=provider.mapping_version
            )
            finding_id = f"{view.view_id}-R{existing + i + 1:02d}"
            x1, y1, x2, y2 = r["bbox"]
            s.add(
                Finding(
                    finding_id=finding_id,
                    view_id=view.view_id,
                    product_id=product_id,
                    item=view.item,
                    camera_id=camera_id,
                    source=source,
                    bbox_x1=int(x1),
                    bbox_y1=int(y1),
                    bbox_x2=int(x2),
                    bbox_y2=int(y2),
                    score=r["score"],
                    part_id=part_id,
                    model_version=provider.model_version,
                    mapping_version=provider.mapping_version,
                )
            )
            regions.append(
                {
                    "region_id": finding_id,
                    "part_id": part_id,
                    "bbox": {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
                    "centroid": {"x": r["centroid"][0], "y": r["centroid"][1]},
                    "area_px": r["area_px"],
                    "score": r["score"],
                    "evidence": {
                        "image_uri": view.image_uri,
                        "error_map_uri": view.error_map_uri,
                    },
                    "model_version": provider.model_version,
                    "mapping_version": provider.mapping_version,
                }
            )

        return {
            "product_id": product_id,
            "camera_id": camera_id,
            "source": source,
            "threshold_mode": threshold_mode,
            "min_area_px": min_area_px,
            "regions": regions,
            "model_version": provider.model_version,
            "mapping_version": provider.mapping_version,
            "definition_version": DEFINITION_VERSION,
        }


# ---------------------------------------------------------------- 도구 2

def compute_inspection_metrics(
    *,
    item: str,
    date_from: str,
    date_to: str,
    model_version: str,
    part_id: str | None = None,
    camera_id: str | None = None,
    review_state: str = "confirmed",
    session=None,
) -> dict:
    """4개 지표를 계산한다. pending/confirmed를 섞지 않으며, 분모 0이면 rate=null."""
    _check_review_state(review_state)
    with _session(session, role="read") as s:
        model_version = _resolve_fusion_run(s, model_version)
        reviews = _fetch_reviews(
            s, item=item, part_id=part_id, camera_id=camera_id,
            date_from=date_from, date_to=date_to, review_state=review_state,
        )
        pred = _predicted_keys(
            s, item=item, part_id=part_id, camera_id=camera_id, model_version=model_version
        )

        def predicted(r) -> bool:
            return (r.product_id, r.part_id, r.camera_id) in pred

        n_defect = sum(1 for r in reviews if r.truth_label == "defect")
        n_normal = len(reviews) - n_defect
        n_miss = sum(
            1 for r in reviews if r.truth_label == "defect" and not predicted(r)
        )
        n_false_alarm = sum(
            1 for r in reviews if r.truth_label == "normal" and predicted(r)
        )
        attempts = _fetch_attempts(
            s, item=item, model_version=model_version, date_from=date_from, date_to=date_to
        )
        n_fail = sum(1 for a in attempts if a.status in FAIL_STATUSES)

        metrics = {
            # 불량 확인 제품 / 부위 검수 제품
            CONFIRMED_DEFECT_RATE: _rate(n_defect, n_defect + n_normal),
            # 놓친 불량 제품 / 부위 불량 확인 제품
            PART_MISS_RATE: _rate(n_miss, n_defect),
            # 잘못 경보한 정상 제품 / 부위 정상 제품
            PART_FALSE_ALARM_RATE: _rate(n_false_alarm, n_normal),
            # 누락·흐림·추론 오류 / 시도 건수
            CAPTURE_PROCESS_FAILURE_RATE: _rate(n_fail, len(attempts)),
        }
        if model_version and model_version.startswith("uncalibrated-scores:"):
            for key in [PART_MISS_RATE,PART_FALSE_ALARM_RATE]:
                metrics[key]={"num":0,"den":0,"rate":None,"reason":"fusion_thresholds_unconfigured"}
        filters = {
            "item": item,
            "part_id": part_id,
            "camera_id": camera_id,
            "date_from": date_from,
            "date_to": date_to,
            "model_version": model_version,
            "review_state": review_state,
        }
        return {
            "filters": filters,
            "metrics": metrics,
            "model_version": model_version,
            "mapping_version": None,
            "definition_version": DEFINITION_VERSION,
        }


# ---------------------------------------------------------------- 도구 3

def _stat_key(filters: dict) -> str:
    return json.dumps(filters, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def query_error_stats(
    *,
    item: str,
    metric: str,
    group_by: list[str],
    date_from: str | None = None,
    date_to: str | None = None,
    model_version: str | None = None,
    min_denominator: int = 1,
    order: str = "desc",
    limit: int = 10,
    session=None,
) -> dict:
    """지표를 group_by로 집계하고, 필터를 모두 포함한 stable stat_key를 붙인다."""
    if metric not in ALL_METRICS:
        raise ToolError(f"지원하지 않는 지표입니다: {metric}")
    group_by = list(group_by or [])
    bad = set(group_by) - GROUPABLE
    if bad:
        raise ToolError(f"지원하지 않는 group_by입니다: {sorted(bad)}")
    if metric == CAPTURE_PROCESS_FAILURE_RATE and set(group_by) - {"model_version"}:
        raise ToolError("capture_process_failure_rate는 model_version으로만 grouping할 수 있습니다")
    if order not in ("desc", "asc"):
        raise ToolError(f"order는 desc 또는 asc여야 합니다: {order}")
    if limit < 1:
        raise ToolError("limit는 1 이상이어야 합니다")
    if min_denominator < 0:
        raise ToolError("min_denominator는 0 이상이어야 합니다")

    if model_version and model_version.startswith("uncalibrated-scores:") and metric in [PART_MISS_RATE,PART_FALSE_ALARM_RATE]:
        return {"item":item,"metric":metric,"group_by":group_by,"rows":[],"order":order,
                "limit":limit,"min_denominator":min_denominator,"model_version":model_version,
                "mapping_version":None,"definition_version":DEFINITION_VERSION,
                "reason":"fusion_thresholds_unconfigured"}

    with _session(session, role="read") as s:
        model_version = _resolve_fusion_run(s, model_version)
        buckets: dict[tuple, list[int]] = {}  # review: [total, defect, miss, fa] / capture: [total, fail]
        if metric == CAPTURE_PROCESS_FAILURE_RATE:
            for a in _fetch_attempts(s, item=item, model_version=model_version,
                                     date_from=date_from, date_to=date_to):
                k = (a.model_version,) if "model_version" in group_by else ()
                b = buckets.setdefault(k, [0, 0, 0, 0])
                b[0] += 1
                if a.status in FAIL_STATUSES:
                    b[1] += 1
        else:
            reviews = _fetch_reviews(
                s, item=item, part_id=None, camera_id=None,
                date_from=date_from, date_to=date_to, review_state="confirmed",
            )
            pred = _predicted_keys(
                s, item=item, part_id=None, camera_id=None, model_version=model_version
            )
            for r in reviews:
                k = tuple(
                    ([r.part_id] if "part_id" in group_by else [])
                    + ([r.camera_id] if "camera_id" in group_by else [])
                    + ([model_version] if "model_version" in group_by else [])
                )
                b = buckets.setdefault(k, [0, 0, 0, 0])
                b[0] += 1
                is_pred = (r.product_id, r.part_id, r.camera_id) in pred
                if r.truth_label == "defect":
                    b[1] += 1
                    if not is_pred:
                        b[2] += 1
                else:
                    if is_pred:
                        b[3] += 1

        rows = []
        for k, b in buckets.items():
            if metric == CAPTURE_PROCESS_FAILURE_RATE:
                num, den = b[1], b[0]
            elif metric == CONFIRMED_DEFECT_RATE:
                num, den = b[1], b[0]
            elif metric == PART_MISS_RATE:
                num, den = b[2], b[1]
            else:  # PART_FALSE_ALARM_RATE
                num, den = b[3], b[0] - b[1]
            if den < min_denominator:
                continue
            group = dict(zip(group_by, k))
            filters = {
                "def": DEFINITION_VERSION,
                "metric": metric,
                "item": item,
                "part_id": group.get("part_id"),
                "camera_id": group.get("camera_id"),
                "model_version": group.get("model_version", model_version),
                "date_from": date_from,
                "date_to": date_to,
                "review_state": "confirmed",
                "min_denominator": min_denominator,
            }
            rate = _rate(num, den)
            rows.append(
                {
                    "group": group,
                    "num": rate["num"],
                    "den": rate["den"],
                    "rate": rate["rate"],
                    "reason": rate["reason"],
                    "stat_key": _stat_key(filters),
                }
            )

        if order == "desc":
            rows.sort(key=lambda r: (r["rate"] is None, -(r["rate"] or 0.0)))
        else:
            rows.sort(key=lambda r: (r["rate"] is None, r["rate"] or 0.0))
        rows = rows[:limit]

        return {
            "item": item,
            "metric": metric,
            "group_by": group_by,
            "rows": rows,
            "order": order,
            "limit": limit,
            "min_denominator": min_denominator,
            "model_version": model_version,
            "mapping_version": None,
            "mapping_verified": False,
            "source_scope": "inspection_attempts" if metric == CAPTURE_PROCESS_FAILURE_RATE else "confirmed_reviews",
            "definition_version": DEFINITION_VERSION,
        }


# ---------------------------------------------------------------- 도구 4

def _decode_stat_key(stat_key: str) -> dict:
    try:
        filters = json.loads(stat_key)
    except (TypeError, json.JSONDecodeError):
        raise ToolError("stat_key를 해석할 수 없습니다")
    if not isinstance(filters, dict) or filters.get("metric") not in ALL_METRICS:
        raise ToolError("stat_key에 유효하지 않은 지표가 들어 있습니다")
    return filters


def _view_evidence(v) -> dict | None:
    if v is None:
        return None
    return {
        "view_id": v.view_id,
        "image_uri": (f"/evidence/{v.view_id}/image" if v.image_uri.startswith("/") else v.image_uri),
        "error_map_uri": (f"/evidence/{v.view_id}/map" if v.error_map_uri and v.error_map_uri.startswith("/") else v.error_map_uri),
        "status": v.status,
    }


def _review_case(session, r: Review, model_version: str | None) -> dict:
    aq=select(Attempt).where(Attempt.product_id==r.product_id)
    if model_version:aq=aq.where(Attempt.model_version==model_version)
    attempt=session.scalar(aq.order_by(Attempt.started_at.desc(),Attempt.attempt_id.desc()).limit(1))
    views = list(session.scalars(select(View).where(View.attempt_id == attempt.attempt_id)).all()) if attempt else []
    vmap = {v.camera_id: v for v in views}
    fq = select(Finding).where(
        Finding.product_id == r.product_id,
        Finding.view_id.in_([v.view_id for v in views]),
        Finding.part_id == r.part_id,
        Finding.camera_id == r.camera_id,
    )
    if model_version:
        fq = fq.where(Finding.model_version == model_version)
    findings = list(session.scalars(fq).all())
    view = vmap.get(r.camera_id)
    first = findings[0] if findings else None
    return {
        "product_id": r.product_id,
        "item": r.item,
        "part_id": r.part_id,
        "camera_id": r.camera_id,
        "truth_label": r.truth_label,
        "prediction": ((attempt.verdict if attempt else None) or (("defect" if findings else "normal") if attempt and attempt.model_version.startswith("mock") else None)),
        "model_version": first.model_version if first else (model_version or (attempt.model_version if attempt else None)),
        "mapping_version": first.mapping_version if first else (views[0].mapping_version if views else None),
        "box_ids": [f.finding_id for f in findings],
        "evidence": {
            "original_uri": view.image_uri if view else None,
            "error_map_uri": view.error_map_uri if view else None,
            "crop_uri": (
                f"mock://crops/{r.product_id}/{r.camera_id}/{first.finding_id}.png" if first else None
            ),
            "all_views": {f"C{i}": _view_evidence(vmap.get(f"C{i}")) for i in range(1, 6)},
        },
        "review": {"state": r.review_state, "reviewer": r.reviewer, "reason": r.reason, "version": r.version, "camera_id": r.camera_id},
    }


def _capture_case(session, a: Attempt) -> dict:
    views = list(
        session.scalars(select(View).where(View.attempt_id == a.attempt_id)).all()
    )
    vmap = {v.camera_id: v for v in views}
    first = views[0] if views else None
    return {
        "product_id": a.product_id,
        "item": a.item,
        "part_id": None,
        "camera_id": None,
        "truth_label": None,
        "prediction": None,
        "model_version": a.model_version,
        "mapping_version": a.mapping_version,
        "box_ids": [],
        "attempt_status": a.status,
        "evidence": {
            "original_uri": first.image_uri if first else None,
            "error_map_uri": first.error_map_uri if first else None,
            "crop_uri": None,
            "all_views": {f"C{i}": _view_evidence(vmap.get(f"C{i}")) for i in range(1, 6)},
        },
        "review": None,
    }


def get_case_evidence(
    *,
    stat_key: str | None = None,
    product_id: str | None = None,
    part_id: str | None = None,
    camera_id: str | None = None,
    limit: int = 20,
    session=None,
) -> dict:
    """stat_key(또는 개별 필터)가 가리키는 지표의 사례 집합을 연다.
    검수 기반 지표는 분모 집합(검수 대상 제품), 캡처 지표는 오류 시도 집합을 반환한다."""
    if limit < 1:
        raise ToolError("limit는 1 이상이어야 합니다")

    filters: dict | None = None
    metric = item = date_from = date_to = model_version = None
    review_state = "confirmed"
    if stat_key:
        filters = _decode_stat_key(stat_key)
        metric = filters["metric"]
        item = filters.get("item")
        part_id = filters.get("part_id", part_id)
        camera_id = filters.get("camera_id", camera_id)
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        model_version = filters.get("model_version")
        review_state = filters.get("review_state", "confirmed")

    with _session(session, role="read") as s:
        cases = []
        if product_id and not stat_key:
            attempt = s.scalar(select(Attempt).where(Attempt.product_id == product_id)
                               .order_by(Attempt.started_at.desc(),Attempt.attempt_id.desc()).limit(1))
            if attempt:
                case = _capture_case(s,attempt)
                current = s.scalar(select(Review).where(Review.product_id==product_id,
                    Review.camera_id==(camera_id or "C1"),Review.review_state=="confirmed")
                    .order_by(Review.reviewed_at.desc()).limit(1))
                case["review"] = ({"state":current.review_state,"reviewer":current.reviewer,
                    "reason":current.reason,"version":current.version,"camera_id":current.camera_id} if current else None)
                case["truth_label"]=attempt.truth_label;case["prediction"]=attempt.verdict
                case["camera_id"]=camera_id or "C1"
                selected=case["evidence"]["all_views"].get(case["camera_id"])
                if selected:
                    case["evidence"]["original_uri"]=selected["image_uri"]
                    case["evidence"]["error_map_uri"]=selected["error_map_uri"]
                boxes=list(s.scalars(select(Finding).where(Finding.view_id.in_(
                    [v["view_id"] for v in case["evidence"]["all_views"].values() if v]))).all())
                case["findings"]=[{"camera_id":f.camera_id,"kind":f.kind,"bbox":[f.bbox_x1,f.bbox_y1,f.bbox_x2,f.bbox_y2],"score":f.score} for f in boxes]
                cases.append(case)
        elif metric == CAPTURE_PROCESS_FAILURE_RATE:
            for a in _fetch_attempts(s, item=item, model_version=model_version,
                                     date_from=date_from, date_to=date_to):
                if a.status in FAIL_STATUSES:
                    cases.append(_capture_case(s, a))
        else:
            reviews = (
                _fetch_reviews(s, item=item, part_id=part_id, camera_id=camera_id,
                               date_from=date_from, date_to=date_to, review_state=review_state)
                if item
                else []
            )
            # 지표 분모 집합에 맞게 truth 필터: miss는 불량 확인, false alarm은 정상 확인 제품
            if metric == PART_MISS_RATE:
                reviews = [r for r in reviews if r.truth_label == "defect"]
            elif metric == PART_FALSE_ALARM_RATE:
                reviews = [r for r in reviews if r.truth_label == "normal"]
            if product_id:
                reviews = [r for r in reviews if r.product_id == product_id]
            for r in reviews:
                cases.append(_review_case(s, r, model_version))

        cases = cases[:limit]
        return {
            "cases": cases,
            "count": len(cases),
            "limit": limit,
            "filters": filters
            or {"product_id": product_id, "part_id": part_id, "camera_id": camera_id,
                "review_state": review_state},
            "model_version": model_version,
            "mapping_version": None,
            "definition_version": DEFINITION_VERSION,
        }


# ---------------------------------------------------------------- 스키마

TOOL_FUNCS = {
    "extract_abnormal_locations": extract_abnormal_locations,
    "compute_inspection_metrics": compute_inspection_metrics,
    "query_error_stats": query_error_stats,
    "get_case_evidence": get_case_evidence,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "extract_abnormal_locations",
            "description": "제품의 특정 칼라 뷰에서 이상 위치를 추출한다. threshold(p95/p99/fixed)와 형태학, connected components, min_area_px로 영역을 뽑고 ROI LUT으로 part_id를 매핑해 findings에 저장한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "camera_id": {"type": "string", "description": "C1~C5"},
                    "source": {"type": "string", "enum": ["anomaly", "defect"], "default": "anomaly"},
                    "threshold_mode": {"type": "string", "enum": ["p95", "p99", "fixed"], "default": "p99"},
                    "min_area_px": {"type": "integer", "default": 24},
                    "threshold_value": {"type": "number", "description": "threshold_mode=fixed일 때 사용할 고정 임계값"},
                },
                "required": ["product_id", "camera_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_inspection_metrics",
            "description": "4개 지표를 계산한다. confirmed_defect_rate=불량 확인 제품/부위 검수 제품, part_miss_rate=놓친 불량 제품/부위 불량 확인 제품, part_false_alarm_rate=잘못 경보한 정상 제품/부위 정상 제품, capture_process_failure_rate=누락·흐림·추론 오류/시도 건수. pending과 confirmed를 섞지 않으며 분모 0이면 rate=null, reason=denominator_zero다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "part_id": {"type": "string"},
                    "camera_id": {"type": "string"},
                    "date_from": {"type": "string", "description": "ISO8601"},
                    "date_to": {"type": "string", "description": "ISO8601"},
                    "model_version": {"type": "string"},
                    "review_state": {"type": "string", "enum": ["pending", "confirmed"], "default": "confirmed"},
                },
                "required": ["item", "date_from", "date_to", "model_version"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_error_stats",
            "description": "지표를 group_by로 집계해 히트맵 등에 쓴다. 각 행에는 num/den/rate와 필터를 모두 포함한 stable한 stat_key가 붙는다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "metric": {"type": "string", "enum": list(ALL_METRICS)},
                    "group_by": {"type": "array", "items": {"type": "string", "enum": ["part_id", "camera_id", "model_version"]}},
                    "date_from": {"type": "string"},
                    "date_to": {"type": "string"},
                    "model_version": {"type": "string"},
                    "min_denominator": {"type": "integer", "default": 1},
                    "order": {"type": "string", "enum": ["desc", "asc"], "default": "desc"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["item", "metric", "group_by"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_case_evidence",
            "description": "stat_key(또는 product_id/part_id/camera_id)가 가리키는 사례 집합과 2D 근거(원본/오차맵/크롭/전체 C1~C5 뷰, 검수 정보)를 반환한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stat_key": {"type": "string"},
                    "product_id": {"type": "string"},
                    "part_id": {"type": "string"},
                    "camera_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": [],
            },
        },
    },
]


# ---------------------------------------------------------------- 추가 도구 (스펙: 검수 요청 / 학습 상태 조회)

def _ensure_user(s, name: str, role: str = "reviewer") -> str:
    """reviewer 이름 → users upsert → user_id 반환."""
    from datetime import datetime
    import uuid as _uuid

    u = s.execute(select(User).where(User.name == name)).scalar_one_or_none()
    if u is None:
        user_id = f"u-{_uuid.uuid4().hex[:10]}"
        s.add(User(user_id=user_id, name=name, role=role,
                   created_at=datetime.now().isoformat(timespec="seconds")))
        s.flush()
        return user_id
    return u.user_id


def request_review(*, product_id: str, reason: str, part_id: str | None = None,
                   camera_id: str | None = None, reviewer: str = "agent") -> dict:
    """사례를 검수 대기열에 등록한다(pending). 기존 라벨은 건드리지 않는다."""
    from datetime import datetime
    import uuid as _uuid

    with _session(role="workflow") as s:
        attempt = s.execute(
            select(Attempt).where(Attempt.product_id == product_id)
            .order_by(Attempt.started_at.desc()).limit(1)
        ).scalar_one_or_none()
        if attempt is None:
            raise ToolError(f"제품을 찾을 수 없습니다: {product_id}")
        review_id = f"req-{_uuid.uuid4().hex[:12]}"
        s.add(Review(
            review_id=review_id, product_id=product_id, item=attempt.item,
            part_id=part_id or "unknown", camera_id=camera_id or "-",
            truth_label=attempt.truth_label or "unknown",
            review_state="pending", reviewer=reviewer, reason=reason,
            reviewed_at=datetime.now().isoformat(timespec="seconds"),
        ))
        attempt.review_status = "pending"
        s.add(attempt)
        queued = s.execute(
            select(Review).where(Review.review_state == "pending")
        ).scalars().all()
        pos = sum(1 for r in queued if r.reviewed_at <= datetime.now().isoformat(timespec="seconds"))
        return {
            "case_id": review_id,
            "product_id": product_id,
            "item": attempt.item,
            "part_id": part_id or "unknown",
            "camera_id": camera_id or "-",
            "review_state": "pending",
            "reason": reason,
            "queued_position": pos,
            "queued_total": len(queued),
            "model_version": attempt.model_version,
            "definition_version": DEFINITION_VERSION,
        }


def get_training_status(*, item: str | None = None) -> dict:
    """학습 상태 조회: 승인(확정) 표본 수, 검수 대기 후보, 보류 후보, 모델 기준선, 배치 진행."""
    with _session(role="read") as s:
        def _count(q):
            return len(s.execute(q).scalars().all())
        conf_q = select(Review).where(Review.review_state == "confirmed")
        pend_q = select(Review).where(Review.review_state == "pending")
        hold_q = select(Attempt).where(Attempt.verdict == "hold", Attempt.status == "completed")
        if item:
            conf_q = conf_q.where(Review.item == item)
            pend_q = pend_q.where(Review.item == item)
            hold_q = hold_q.where(Attempt.item == item)
        confirmed = _count(conf_q)
        pending = _count(pend_q)
        hold = _count(hold_q)
        by_model = {}
        q = select(Attempt).where(Attempt.status == "completed")
        if item:
            q = q.where(Attempt.item == item)
        for a in s.execute(q).scalars().all():
            by_model[a.model_version] = by_model.get(a.model_version, 0) + 1
        batch_total = sum(by_model.get(k, 0) for k in by_model if k.startswith("fusion-v1"))
        fp_fn = {"FP": 0, "FN": 0}
        for r in s.execute(select(Review).where(Review.fp_fn.isnot(None))).scalars().all():
            fp_fn[r.fp_fn] = fp_fn.get(r.fp_fn, 0) + 1
        return {
            "approved_samples": {"num": confirmed, "note": "검수 확정(confirmed) 표본"},
            "pending_candidates": {"num": pending, "note": "검수 대기(pending)"},
            "hold_candidates": {"num": hold, "note": "퓨전 보류(엇갈림) 제품 — 검수 우선 후보"},
            "confirmed_fp_fn": {"FP": fp_fn.get("FP", 0), "FN": fp_fn.get("FN", 0),
                                "denominator": fp_fn.get("FP", 0) + fp_fn.get("FN", 0)},
            "model_baselines": by_model,
            "fusion_processed_products": batch_total,
            "item": item,
            "definition_version": DEFINITION_VERSION,
        }


TOOL_FUNCS["request_review"] = request_review
TOOL_FUNCS["get_training_status"] = get_training_status


def get_final_performance(*, item: str | None = None) -> dict:
    """최종 퓨전 성능 리포트(final_performance) 요약을 조회한다.

    전체 추론·DB 반영·에이전트 검증이 끝나 latest.json이 생기면 그 값을,
    아직 없으면 현재 진행 상태(대기 중/계산 중)를 반환한다. 수치는 실데이터
    리포트 기준이며 기준선 v1과 나란히 비교할 수 있게 포함한다.
    """
    from .status import (final_performance_payload, final_performance_state,
                         final_performance_summary)

    payload = final_performance_payload()
    summary = final_performance_summary(payload)
    if not summary["available"]:
        summary["state"] = final_performance_state(payload=payload)
    return {
        "state": summary["state"],
        "available": summary["available"],
        "is_fixture": summary["is_fixture"],
        "item": item,
        "metrics": summary["metrics"],
        "model_version": summary["model_version"],
        "baseline_v1": summary["baseline_v1"],
        "report_path": summary["report_path"],
        "definition_version": DEFINITION_VERSION,
    }


TOOL_FUNCS["get_final_performance"] = get_final_performance

def query_spatial_evidence(**kwargs):
    from .spatial_tools import query_spatial_evidence as implementation
    from fastapi import HTTPException
    try:return implementation(**kwargs)
    except ValueError as error:raise ToolError(str(error)) from error
    except HTTPException as error:
        if error.status_code in (404,409,503):return {'status':'unavailable','reason':str(error.detail),'hotspots':[]}
        raise ToolError(str(error.detail)) from error

TOOL_FUNCS['query_spatial_evidence']=query_spatial_evidence
TOOL_SCHEMAS.append({'type':'function','function':{'name':'query_spatial_evidence',
    'description':'저장된 개별 제품/단일 카메라의 공간 모델 신호와 실제 픽셀 위치를 조회한다. 주요부위/세부부위별 상위 셀과 표본 부족을 반환한다. 확정 불량/FP/FN/공식 퓨전이 아니며 카메라를 합산하지 않는다. 실제 맵이 없으면 unsupported다. evidence_link는 등록된 GUI 공간 근거 링크다.',
    'parameters':{'type':'object','properties':{'item':{'type':'string'},'product_id':{'type':'string'},'camera':{'type':'string','enum':['C1','C2','C3','C4','C5']},'region_id':{'type':'string'},'model':{'type':'string','enum':['rt','hvq']},'method':{'type':'string'},'resolution':{'type':'integer','enum':[16,32,64,128]},'limit':{'type':'integer','minimum':1,'maximum':20}},'required':['item']}}})

TOOL_SCHEMAS.append({
    "type": "function",
    "function": {
        "name": "request_review",
        "description": "사례를 검수 대기열(pending)에 등록한다. 사례 ID를 반환하며, 대기 상태와 큐 길이를 함께 알려준다.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "reason": {"type": "string", "description": "검수 요청 이유"},
                "part_id": {"type": "string"},
                "camera_id": {"type": "string"},
                "reviewer": {"type": "string", "default": "agent"},
            },
            "required": ["product_id", "reason"],
        },
    },
})
TOOL_SCHEMAS.append({
    "type": "function",
    "function": {
        "name": "get_training_status",
        "description": "학습 상태를 조회한다: 승인(확정) 표본 수, 검수 대기 후보 수, 퓨전 보류 후보 수, FP/FN 확정(분자/분모), 모델 기준별 처리 제품 수.",
        "parameters": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "품목 필터(미지정이면 전체)"},
            },
            "required": [],
        },
    },
})
TOOL_SCHEMAS.append({
    "type": "function",
    "function": {
        "name": "get_final_performance",
        "description": "저장된 퓨전 성능을 조회한다. metrics.evaluation_scope가 all_inferred_products_reference이면 전체 추론 제품의 참고 집계이며 Validation 포함/학습 중복 미확인을 설명한다. test_products와 test_f1_micro는 별도 Test 평가다. 부위 검수 통계와 혼동하지 않는다. 보고서가 없으면 산출 상태를 반환한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "품목 필터(리포트 전체 요약에는 영향 없음)"},
            },
            "required": [],
        },
    },
})


def submit_review(*, product_id: str, camera_id: str, bbox: list[float],
                  truth_label: str, fp_fn: str | None = None,
                  reviewer: str = "gui", reason: str | None = None,
                  expected_version: int | None = None) -> dict:
    """검수 결과를 반영한다: 수동 박스(finding) + 확정 리뷰(reviews) 기록 후 지표 스냅샷 재계산.

    bbox는 원본 해상도 좌표 [x1,y1,x2,y2]. truth_label ∈ {defect, normal}.
    """
    from datetime import datetime
    import uuid as _uuid

    if truth_label not in ("defect", "normal"):
        raise ToolError("truth_label은 defect|normal 이어야 합니다")
    if fp_fn not in (None, "FP", "FN"):
        raise ToolError("fp_fn은 FP|FN|null 이어야 합니다")
    if len(bbox) != 4:
        raise ToolError("bbox는 [x1,y1,x2,y2] 4개여야 합니다")

    with _session(role="workflow") as s:
        attempt = s.execute(
            select(Attempt).where(Attempt.product_id == product_id)
            .order_by(Attempt.started_at.desc()).limit(1)
        ).scalar_one_or_none()
        if attempt is None:
            raise ToolError(f"제품을 찾을 수 없습니다: {product_id}")
        item = attempt.item
        view = s.execute(
            select(View).where(View.attempt_id == attempt.attempt_id, View.camera_id == camera_id)
            .order_by(View.view_id.desc()).limit(1)
        ).scalar_one_or_none()
        view_id = view.view_id if view else f"{product_id}:{camera_id}"
        rid = f"rev-{_uuid.uuid4().hex[:12]}"
        x1, y1, x2, y2 = (float(v) for v in bbox)
        import math
        if not all(math.isfinite(v) for v in (x1, y1, x2, y2)) or not (0 <= x1 < x2 and 0 <= y1 < y2):
            raise ToolError("bbox는 유한한 양의 면적 좌표여야 합니다")
        if view is None:
            raise ToolError("검수할 시점이 없습니다")
        if (view.width and x2 > view.width) or (view.height and y2 > view.height):
            raise ToolError("bbox가 원본 이미지 범위를 벗어납니다")
        now = datetime.now().isoformat(timespec="seconds")
        reviewer_id = _ensure_user(s, reviewer)

        # 동시 검수: 같은 (product_id, camera_id) 확정 리뷰가 이미 있으면 수정 모드
        existing = s.execute(
            select(Review).where(Review.product_id == product_id,
                                 Review.camera_id == camera_id,
                                 Review.review_state == "confirmed")
            .order_by(Review.reviewed_at.desc()).limit(1)
        ).scalar_one_or_none()
        version_out = 1
        if existing is not None:
            if expected_version is None:
                raise ReviewConflict(
                    f"이미 다른 사용자가 검수함 (review_id={existing.review_id}, "
                    f"version={existing.version}). 수정하려면 expected_version을 별표로 본다.")
            if existing.version != expected_version:
                raise ReviewConflict(
                    "이미 다른 사용자가 검수함 — 버전 충돌 "
                    f"(기대 {expected_version} vs 실제 {existing.version}). "
                    "새로고침 후 다시 시도하세요.")
            existing.truth_label = truth_label
            existing.fp_fn = fp_fn
            existing.corrected_label = truth_label
            existing.reviewer = reviewer
            existing.reviewer_id = reviewer_id
            existing.reason = reason
            existing.reviewed_at = now
            existing.updated_at = now
            existing.version = existing.version + 1
            s.add(existing)
            rid = existing.review_id
            version_out = existing.version
        else:
            s.add(Review(
                review_id=rid, product_id=product_id, item=item, part_id="unknown",
                camera_id=camera_id, truth_label=truth_label, review_state="confirmed",
                reviewer=reviewer, reviewer_id=reviewer_id, reason=reason,
                reviewed_at=now, updated_at=now, version=1,
                fp_fn=fp_fn, corrected_label=truth_label,
            ))
        s.merge(Finding(
            finding_id=f"{rid}:box", view_id=view_id, product_id=product_id,
            item=item, camera_id=camera_id, source="manual", kind="manual_box",
            bbox_x1=int(x1), bbox_y1=int(y1), bbox_x2=int(x2), bbox_y2=int(y2),
            score=1.0, part_id="unknown",
            model_version="human-review", mapping_version=attempt.mapping_version,
        ))
        attempt.review_status = "confirmed"
        s.add(attempt)

    from .recompute import enqueue_item_metrics
    snapshot_note = enqueue_item_metrics(item)
    return {
        "review_id": rid, "product_id": product_id, "camera_id": camera_id,
        "truth_label": truth_label, "fp_fn": fp_fn, "review_state": "confirmed",
        "version": version_out,
        "bbox": [int(x1), int(y1), int(x2), int(y2)],
        "snapshot": snapshot_note,
        "definition_version": DEFINITION_VERSION,
    }


TOOL_FUNCS["submit_review"] = submit_review
TOOL_SCHEMAS.append({
    "type": "function",
    "function": {
        "name": "submit_review",
        "description": "검수 결과를 반영한다: 2D 근거 위의 수동 박스를 findings에 저장하고, 리뷰를 확정(confirmed, FP/FN 분류)으로 기록한 뒤 지표 스냅샷을 재계산한다.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "camera_id": {"type": "string", "description": "C1~C5"},
                "bbox": {"type": "array", "items": {"type": "number"},
                         "description": "원본 해상도 [x1,y1,x2,y2]"},
                "truth_label": {"type": "string", "enum": ["defect", "normal"]},
                "fp_fn": {"type": "string", "enum": ["FP", "FN"]},
                "reviewer": {"type": "string", "default": "gui"},
                "reason": {"type": "string"},
                "expected_version": {"type": "integer"},
            },
            "required": ["product_id", "camera_id", "bbox", "truth_label"],
        },
    },
})
