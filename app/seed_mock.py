"""Deterministic mock 데이터 시딩. 기존 데이터는 삭제 후 다시 만든다.

시나리오(제품×부위 단위, 시드 고정):
- truth: 35% 불량
- 불량이면 70% 확률로 검출(finding 생성), 아니면 miss
- 정상이면 15% 확률로 오경보(finding 생성)
- 검수 상태는 85% confirmed, 15% pending
- 시도의 10%는 캡처/추론 실패 상태
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import delete

from .db import configure, get_session
from .models import Attempt, Finding, Review, View
from .providers.mock import stable_seed
from .rois import MAPPING_VERSION, LUT

MODEL_VERSION = "mock-anomaly-v1"
FAIL_STATUSES = ("capture_missing", "capture_blurred", "inference_error")
CAMERAS = ("C1", "C2", "C3", "C4", "C5")
BASE_TIME = datetime(2026, 11, 10, 9, 0, 0)

ITEMS = {
    "toothbrush": [("bristle", "C1"), ("neck", "C2"), ("handle", "C3")],
    "toy": [("surface", "C1"), ("edge", "C2"), ("joint", "C3")],
}


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def seed_mock(session=None, n_toothbrush: int = 24, n_toy: int = 16, base_seed: int = 42) -> dict:
    own = session is None
    if own:
        configure()
        session = get_session()

    for model in (Finding, Review, View, Attempt):
        session.execute(delete(model))

    summary = {"attempts": 0, "views": 0, "findings": 0, "reviews": 0, "failures": 0}
    seq = 0
    for item, parts in ITEMS.items():
        n = n_toothbrush if item == "toothbrush" else n_toy
        prefix = "TOO" if item == "toothbrush" else "TOY"
        for i in range(n):
            pid = f"{prefix}-{i + 1:04d}"
            seq += 1
            rng = np.random.default_rng(stable_seed(str(base_seed), pid))
            started = BASE_TIME + timedelta(hours=3 * seq)

            status = "completed"
            if float(rng.random()) < 0.10:
                status = str(rng.choice(FAIL_STATUSES))
                summary["failures"] += 1
            session.add(
                Attempt(
                    attempt_id=f"ATT-{pid}",
                    product_id=pid,
                    item=item,
                    started_at=_iso(started),
                    status=status,
                    model_version=MODEL_VERSION,
                    mapping_version=MAPPING_VERSION,
                )
            )
            summary["attempts"] += 1

            missing_cam = str(rng.choice(CAMERAS))
            blurred_cam = str(rng.choice(CAMERAS))
            for cam in CAMERAS:
                if status == "capture_missing" and cam == missing_cam:
                    continue
                vstatus = "blurred" if (status == "capture_blurred" and cam == blurred_cam) else "ok"
                session.add(
                    View(
                        view_id=f"V-{pid}-{cam}",
                        attempt_id=f"ATT-{pid}",
                        product_id=pid,
                        item=item,
                        camera_id=cam,
                        image_uri=f"mock://images/{item}/{pid}/{cam}.png",
                        error_map_uri=f"mock://errmaps/{item}/{pid}/{cam}.png",
                        status=vstatus,
                        model_version=MODEL_VERSION,
                        mapping_version=MAPPING_VERSION,
                    )
                )
                summary["views"] += 1

            for part_id, cam in parts:
                srng = np.random.default_rng(stable_seed(str(base_seed), pid, part_id))
                is_defect = float(srng.random()) < 0.35
                detected = float(srng.random()) < 0.70
                false_alarm = float(srng.random()) < 0.15
                make_finding = (is_defect and detected) or ((not is_defect) and false_alarm)
                review_state = "pending" if float(srng.random()) < 0.15 else "confirmed"
                reviewer = str(srng.choice(["qa-1", "qa-2", "qa-3"]))
                session.add(
                    Review(
                        review_id=f"REV-{pid}-{part_id}",
                        product_id=pid,
                        item=item,
                        part_id=part_id,
                        camera_id=cam,
                        truth_label="defect" if is_defect else "normal",
                        review_state=review_state,
                        reviewer=reviewer,
                        reason="검수 대기" if review_state == "pending" else None,
                        reviewed_at=_iso(started + timedelta(minutes=40)),
                    )
                )
                summary["reviews"] += 1

                if make_finding:
                    rois = dict(LUT[item][cam])
                    rx1, ry1, rx2, ry2 = rois[part_id]
                    bw = int(srng.integers(16, min(48, rx2 - rx1)))
                    bh = int(srng.integers(16, min(48, ry2 - ry1)))
                    x1 = int(srng.integers(rx1, rx2 - bw))
                    y1 = int(srng.integers(ry1, ry2 - bh))
                    source = "anomaly" if float(srng.random()) < 0.6 else "defect"
                    session.add(
                        Finding(
                            finding_id=f"F-{pid}-{part_id}",
                            view_id=f"V-{pid}-{cam}",
                            product_id=pid,
                            item=item,
                            camera_id=cam,
                            source=source,
                            bbox_x1=x1,
                            bbox_y1=y1,
                            bbox_x2=x1 + bw,
                            bbox_y2=y1 + bh,
                            score=round(float(srng.uniform(0.55, 0.99)), 4),
                            part_id=part_id,
                            model_version=MODEL_VERSION,
                            mapping_version=MAPPING_VERSION,
                        )
                    )
                    summary["findings"] += 1

    session.commit()
    if own:
        session.close()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic mock inspection data")
    parser.add_argument("--db", default=None, help="DATABASE_URL (기본: sqlite:///./inspection.db)")
    parser.add_argument("--toothbrush", type=int, default=24)
    parser.add_argument("--toy", type=int, default=16)
    args = parser.parse_args()

    configure(args.db)
    session = get_session()
    summary = seed_mock(
        session=session, n_toothbrush=args.toothbrush, n_toy=args.toy
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
