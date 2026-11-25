# Detailed dashboard models and high-visibility heatmap

2026-11-24. Display implementation and isolated regression checks only. No production DB, model, preprocessing, fusion policy, thresholds, inference/backfill/import jobs or server were changed or restarted.

## Product detail

Thirty existing category templates now include103 additional detail surfaces. Details remain under existing parent region IDs; they do not create new inspection/ROI regions. Approximate templates, not reconstructed CAD.

Examples: toothbrush rounded head/individual filaments/rubber grip/collar; USB real rectangular socket/tongue/contact fingers; jack bore sleeve; terminal cross-slotted screws/wire entries/separators; PCB traces/eyelets/SMDs/chip pins/capacitor cap; battery terminal/isolation ring/positive mark/pouch seal; cap lip/grooves; ring rim/core relief; frame fasteners; zipper interlocking teeth/slider/pull-tab/stitching. SIM tray uses a thin rectangular opening with an edge lip and side tab, not the old generic circular opening.

The previous nine-family system and toothbrush handle/neck/bristle and toy surface/edge/joint IDs are retained. Mesh factories and each detail are deterministic; template arrays/definitions are frozen and carry their category identity. Bounds include all detail geometry. The largest measured template has23,892 triangles (zipper), under45,000. This is a geometry count, not measured GPU time.

## Rendering and inspection display

Local RoomEnvironment/PMREM studio reflections (no HDR downloads), distinct metal/rubber/plastic/board/wood/contact materials, stage/edge light, single-frame contact shadows, demand rendering and dpr≤1.5. The WebGL context/environment is retained across category changes; product subtree/shadows have category keys. Switching clears render lists and color/depth/stencil buffers. Geometry/edges/material ownership and environment textures have disposal paths.

Initial display angles expose USB/jack/PCB interfaces and toothbrush bristles; they are display angles, not C1–C5 calibration.

Heatmap now uses a separate unlit surface overlay rather than relying on PBR color. The same geometry/depth offset keeps the layer aligned, including details in the same region. Modes: 재질 / 겹쳐 보기 / 히트맵; overlay opacity25–100%, default88%; heatmap-only100%. Saturated cyan/yellow/red palette, clear selection outlines, selected/hovered percentage and numerator/denominator, enlarged legend and numerical part-rate cards. Display controls never modify measured rates, API query filters or decision thresholds.

**Unverified/missing/zero-denominator areas remain neutral.** Real3D projection still requires mapping_verified and mapping_version; this central API metadata remains missing in the legacy integration. The UI states this rather than inventing hot spots. Numeric part cards can display genuine API aggregates independently of physical projection. No pixel anomaly location is synthesized from a part-level rate.

## sim_card_set / toothbrush mixing report

User reported occasional mixed appearance. A confirmed stale-data path existed: changing category did not immediately clear old statistics, and old cases/metric responses could arrive after the new category and repopulate the display. All three request generations are now invalidated on category change; previous stats/cases/cards/selections/focus are cleared, and visual consumers reject statistics whose item differs from the current item.

Rendering hardening: category+region+surface namespaces; immutable category-owned definitions; keyed product groups; ignored stale pointer handlers; explicit render-buffer/list reset. The SIM template has only body/tab, never handle/neck/bristle. Rapid A→B→A→B deferred-response tests and repeated SIM/brush mesh ownership tests pass. The actual browser geometry-overlap report has not been reproduced or verified resolved under the sandbox; do not claim the precise GPU cause is established.

## Verification artifacts

Final current-code results: **105 Vitest tests passed (15 files), ESLint passed, TypeScript+production build passed**. Final build13.48s; existing large-chunk warning remains. One earlier build was interrupted withSIGTERM; it was rerun with a bounded Node heap/two Go threads at low priority and the final result is the successful build-final.log, not the interrupted log. Protected inference/config hashes unchanged; hardcoded HEX violations0. No new package installed. Backend/Python inspection code was not modified in this follow-up.

Current tests/results are in reports/gui_validation/detail3d/{vitest-final,eslint-final,build-final,integrity}.log. Geometry inventory: geometry-complexity.json. All30 categories have finite bounds/coordinates and pass the combined detail triangle budget. Existing source/config protection hashes match and hardcoded color violations remain0.

Software preview: reports/gui_validation/detail3d/geometry-review.png. It is generated from actual display mesh vertices and visually inspected, **not a live GUI/PBR screenshot**. The review led to a rounded toothbrush head, a longer handle and interface-facing initial views. Regenerate with:

```bash
cd /home/geonug/agent
GOMAXPROCS=2 nice -n 10 node scripts/export_mesh_previews.mjs /tmp/detailed-mesh-preview.json
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 nice -n 10 .venv/bin/python scripts/render_mesh_previews.py /tmp/detailed-mesh-preview.json
```

Latest host browser acceptance, reflection appearance, actual rapid-switch render behavior and GPU/memory measurements remain UNVERIFIED. Existing host capture script now captures material/overlay/heatmap modes; it does not inject fake inspection rates. To inspect: refresh the current GUI, select a category, use material/overlay/heatmap and camera controls, then switch repeatedly between toothbrush and sim_card_set. Actual unknown data should stay neutral.


### 품목 전환 3D 중첩 재보고 후속 — 2026-11-24

IMPLEMENTED: 이전 수정 후에도 중첩된다는 재보고 반영. Scene.tsx의 Canvas를 품목별 CategoryScene 전체 key로 분리하여 카테고리 간 React Three Fiber root/renderer 재사용을 제거했다. 분리된 이전 캔버스는 microtask에서 animation loop/render lists/renderer/context를 해제한다. 연결 중인 StrictMode 캔버스는 파괴하지 않는다. 설치된 R3F 기본 unmount 해제는500ms 지연됨을 확인했으나 실제 화면 중첩의 확정 원인으로 주장하지 않는다.

VERIFIED: 현재 코드 Vitest109통과(16파일), ESLint통과, TypeScript+Production Build통과(11.16초), 보호된추론/config해시동일,토큰외HEX0. 신규4테스트: 분리키/해제1회/StrictMode보호/이전정리가새렌더러에영향없음. 로그 reports/gui_validation/category-overlap/{vitest,eslint,build,integrity}.log. 신규패키지없음, 운영프로세스·DB·모델·설정·서버재시작없음.

BLOCKED: 실제 브라우저 중첩 재현·시각적 해결확인은 기존 샌드박스 실행제약으로 미완료. 별도개발서버에서 `nice -n 15 node scripts/check_category_overlap.mjs` 실행 가능. 사용가능 품목 정방향/역방향 및 칫솔·SIM 재전환에서 단일Canvas/단일제품그룹/foreign category없음/renderer교체를 실제 장면그래프로 검사하고 스크린샷을 남긴다. 운영쓰기요청차단/보안샌드박스유지. 구문검사통과, 실제브라우저결과는미생성. 기존HMR화면은 새로고침후 확인필요.
