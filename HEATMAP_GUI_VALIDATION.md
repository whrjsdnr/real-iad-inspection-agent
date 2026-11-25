> 2026-11-25 최신: MV_HEATMAP_REUSE_REPORT.md / MV_MASK_API_404_FIX_REPORT.md / TEAM_DATA_SHARING_REPORT.md / FUSION_POLICY_COMPARISON.md 우선. 현재2D실데이터/공유API는구현·수치검증, 3D물리표면투영과호스트브라우저는미완료. 최신Python128/프런트131통과.

# 공간 히트맵 GUI 최종 검증 — 2026-11-24

| 범위 | 상태 | 근거 |
|---|---|---|
| RT실저장박스 공간계산 | VERIFIED | 30품목60제품/1,088격자, 단위테스트/실제handler검사 |
| 칫솔실HVQ공간계산 | VERIFIED | SHA일치 실제224²맵5장 |
| 지퍼HVQ | 미지원 | 실제맵없음, 스칼라로생성하지않음 |
| 계층ROI/모드/투명도/상세클릭/hover/hotspot/확대 | IMPLEMENTED | 최신TS/Build/Vitest통과; 라이브미확인 |
| 실제이미지ROI/공간분포 | VERIFIED | survey6장+동일표본 비교이미지 직접검토 |
| 실제브라우저/스크린샷 | BLOCKED | 기존Chromium sandbox제약; 새서비스socket생성EPERM |
| 물리3D UV표면투영 | 미지원 | 검증된표면대응없어2D fallback |
| 나머지28품목주요ROI공간처리 | IMPLEMENTED | 등록시점공통계산; 의미적세부ROI는PARTIAL |
| 전수제품군공간집계 | NOT_STARTED | 제품간자세정합미검증, 현재개별제품만 |
| 팀공유서비스 | IMPLEMENTED | 인증/읽기전용검사통과, 실제호스트기동필요 |

## 이번코드기준 실행검증

- Python전체120 passed,4 skipped,142.15초: reports/gui_validation/spatial/pytest-all.log.
- Vitest121 passed/19파일: vitest-final.log. ESLint통과: eslint-final.log. TypeScript+Production Build통과6.08초: build-final.log. 500kB청크경고는남아있다.
- ROI/계층/중복박스/coverage/nativebin/미지원/API캐시/도구링크/공유인증/쓰기거부/기존회귀를검사했다. 실제LLM호출/추론은실행하지않았다.
- 실제캐시handler직접조회16건통과: handler-real-data-validation.json. **네트워크HTTP 검증이아니다.** ASGI스레드작업은 이환경에서단순lambda도timeout이관측돼 중단했다. 이를운영API timeout원인으로단정하지않는다.
- 보호자산해시동일, 소스색토큰위반0: integrity-final.log. 신규패키지설치없음.

## 실제검토한이미지

reports/spatial_heatmap/primary-spatial-comparison.jpg는 같은제품/같은ROI의 단일색 대비 공간신호, roi-survey-01.jpg~06.jpg는 30품목×5시점원본을표시한다. 개발용소프트웨어오버레이이며 브라우저스크린샷이아니다. 칫솔국소신호와 지퍼RT분포를원본에대조했다. missingHVQ를패턴으로채우지않았다.

## 호스트에서남은확인

TEAM_SHARING_GUIDE.md대로 별도서비스를켜고 capture_spatial_validation.mjs를실행한다. 대시보드→칫솔/지퍼→모델검출히트맵에서 제품/C1–C5/RT-HVQ-중첩/해상도/투명도/hover/클릭을확인한다. 원본영상과근거위치,미관측투명/표본부족표시를눈으로검토한다. 챗봇의‘선택부위공간근거조회’→근거링크로해당GUI가선택되는지확인한다.

초기로딩/회전프레임/메모리누수/실제네트워크API속도는미측정이다. 캡처스크립트가수집하는 fetch/draw/지원시heap은추정값으로대체하지않는다. 운영프로세스는중단/재시작하지않았고 운영DB쓰기는실행하지않았다. 호스트PID가보이지않아부하영향이0이라고계측으로보증하지는않는다.

## 주요변경파일

app/spatial_heatmap.py, app/spatial_api.py, app/team_api.py, app/part_api.py, app/readonly_api.py, app/tools.py, app/api.py, agent.py; config/spatial_heatmap.json, config/spatial_regions.json; scripts/derive_spatial_heatmaps.py, review_spatial_data.py, validate_spatial_api.py, setup_team_share.py, start_team_share.sh, capture_spatial_validation.mjs; inspection-gui/src/components/SpatialHeatmapPanel.tsx, SpatialEvidenceLink.tsx, CenterPanel.tsx, three/spatialGrid.ts, spatialActions.ts, guiActions.ts, store.ts, ChatPage/TopBar/Nav/Dashboard関連; tests/test_spatial_*.py, test_team_sharing.py 및 프런트 테스트。Git 메타데이터가 없어 변경 목록은 기존 기준 SHA와 비교한 reports/gui_validation/integrity.json을 참고한다.

추가 실제 검토: `reports/spatial_heatmap/primary-hierarchical-roi-overlay.jpg`에서 칫솔·지퍼 C1–C5의 부모/자식 경계를 직접 확인했다. 지퍼의 영상상 상하/좌우 구분이 금속열·직물에 대응하며, 굴곡진 금속 끝의 일부는 폴리곤 밖으로 남는다. ROI 외부를 강제 배정하지 않는다. 칫솔 C1의 끝/중앙/기저 구간은 영상 기반 구간이며 C2–C5에 이를 회전 복제하지 않았다. 이 이미지는 브라우저 캡처가 아니다. 재생성: `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/review_spatial_data.py`.
