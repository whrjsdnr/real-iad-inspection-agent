"""Read-only endpoints for derived, image-bound region evidence."""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from .part_heatmap import load_artifact, summarize_artifact, fingerprint

router = APIRouter()
from .spatial_api import router as spatial_router
router.include_router(spatial_router)
from .ground_truth_api import router as ground_truth_router
router.include_router(ground_truth_router)
from .surface_api import router as surface_router
router.include_router(surface_router)


@router.get('/parts/heatmap')
async def heatmap(item: str, camera: str | None = Query(default=None, pattern='^C[1-5]$'),
            model_version: str | None = None, date_from: str | None = None, date_to: str | None = None):
    artifact = load_artifact()
    if artifact is None:
        raise HTTPException(503, '부위 근거 집계가 없습니다. derive_part_heatmap.py로 등록 ROI와 저장 결과를 집계하세요.')
    return summarize_artifact(artifact, item, camera, model_version, date_from, date_to)


@router.get('/parts/evidence/{case_id}/{camera}')
def image(case_id: str, camera: str):
    artifact = load_artifact()
    if artifact:
        for case in artifact['cases']:
            if case['case_id'] != case_id:
                continue
            for view in case['views']:
                if view['camera'] == camera:
                    try:
                        if fingerprint(view['image_path']) == view['image_sha256']:
                            return FileResponse(view['image_path'], media_type='image/jpeg')
                    except OSError:
                        pass
    raise HTTPException(404, '등록된 원본 근거를 찾을 수 없습니다.')
