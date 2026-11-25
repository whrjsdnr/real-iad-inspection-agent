"""mock 오차 맵 추출 영역이 ROI LUT으로 올바른 part_id에 매핑되는지 검증."""
from sqlalchemy import select

from app.models import Finding
from app.rois import IMAGE_H, IMAGE_W, map_bbox_to_part
from app.tools import extract_abnormal_locations


def _extract_first_nonempty(seeded_session, source="anomaly", min_area_px=8):
    for pid_prefix in ("TOO", "TOY"):
        for i in range(1, 25):
            pid = f"{pid_prefix}-{i:04d}"
            for cam in ("C1", "C2", "C3", "C4", "C5"):
                res = extract_abnormal_locations(
                    product_id=pid,
                    camera_id=cam,
                    source=source,
                    threshold_mode="p99",
                    min_area_px=min_area_px,
                    session=seeded_session,
                )
                has_real_part = any(r["part_id"] != "unknown" for r in res["regions"])
                if has_real_part:
                    return res, pid_prefix
    raise AssertionError("mock 오차 맵에서 부위로 매핑되는 영역이 추출되지 않았다")


ITEM_BY_PREFIX = {"TOO": "toothbrush", "TOY": "toy"}


def test_regions_mapped_to_roi_lut(seeded_session):
    res, prefix = _extract_first_nonempty(seeded_session)
    item = ITEM_BY_PREFIX[prefix]
    assert res["model_version"] == "mock-anomaly-v1"
    assert res["mapping_version"] == "roi-lut-v1"
    assert res["definition_version"] == "metrics-v1"

    mapped_real = 0
    for region in res["regions"]:
        bbox = (
            region["bbox"]["x1"], region["bbox"]["y1"],
            region["bbox"]["x2"], region["bbox"]["y2"],
        )
        # bbox 좌표와 면적이 유효
        assert 0 <= bbox[0] < bbox[2] <= IMAGE_W
        assert 0 <= bbox[1] < bbox[3] <= IMAGE_H
        assert region["area_px"] >= 8
        assert 0.0 <= region["score"] <= 1.0
        # LUT으로 재계산한 part_id와 도구가 반환한 part_id가 일치
        expected_part = map_bbox_to_part(item, res["camera_id"], bbox)
        assert region["part_id"] == expected_part
        if region["part_id"] != "unknown":
            mapped_real += 1
        # 근거 URI와 버전
        assert region["evidence"]["image_uri"].startswith("mock://")
        assert region["evidence"]["error_map_uri"].startswith("mock://")
        assert region["model_version"]
        assert region["mapping_version"]

    assert mapped_real >= 1, "최소 1개 이상의 영역이 실제 부위로 매핑되어야 한다"


def test_findings_saved(seeded_session):
    res, _ = _extract_first_nonempty(seeded_session)
    view_id = f"V-{res['product_id']}-{res['camera_id']}"
    rows = seeded_session.scalars(
        select(Finding).where(Finding.view_id == view_id)
    ).all()
    region_ids = {r["region_id"] for r in res["regions"]}
    saved_ids = {f.finding_id for f in rows}
    assert region_ids <= saved_ids
    for f in rows:
        assert f.model_version == "mock-anomaly-v1"
        assert f.mapping_version == "roi-lut-v1"


def test_extract_is_deterministic(seeded_session):
    r1, _ = _extract_first_nonempty(seeded_session)
    r2 = extract_abnormal_locations(
        product_id=r1["product_id"], camera_id=r1["camera_id"],
        source="anomaly", threshold_mode="p99", min_area_px=8,
        session=seeded_session,
    )
    key = lambda regions: [
        (r["part_id"], r["bbox"], r["centroid"], r["area_px"], r["score"])
        for r in regions
    ]
    assert key(r1["regions"]) == key(r2["regions"])
    # 두 번째 호출은 시퀀스 번호가 이어져서 다른 region_id를 발급
    assert r1["regions"][0]["region_id"] != r2["regions"][0]["region_id"]


def test_defect_source_extract(seeded_session):
    res, prefix = _extract_first_nonempty(seeded_session, source="defect")
    item = ITEM_BY_PREFIX[prefix]
    assert res["model_version"] == "mock-defect-v1"
    for region in res["regions"]:
        bbox = (
            region["bbox"]["x1"], region["bbox"]["y1"],
            region["bbox"]["x2"], region["bbox"]["y2"],
        )
        assert region["part_id"] == map_bbox_to_part(item, res["camera_id"], bbox)


def test_extract_unknown_view_raises(seeded_session):
    import pytest

    from app.tools import ToolError

    with pytest.raises(ToolError):
        extract_abnormal_locations(
            product_id="NOPE-0000", camera_id="C1", session=seeded_session
        )
