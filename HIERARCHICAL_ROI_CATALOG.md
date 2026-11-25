# 계층형 ROI 카탈로그

설정: `config/spatial_regions.json`. 기존 `config/part_heatmap_regions.json`과 주요 region_id를 유지한다. parent_region_id의 존재/순환/중복을 검사한다. 부모와 자식은 대체 조회 단위이며 합산하지 않는다. 검증되지 않은 신뢰도 수치는 생성하지 않는다.

- toothbrush: bristle → bristle_tip, bristle_center, bristle_base(C1 영상상의 구간). C2–C5는 주요 부위만. neck는 미주석 상태 유지. 사용자 요청으로 제거된 손잡이는 복구하지 않았다.
- zipper: teeth/tape 유지. C1,C2,C4에 상·하 metal row/fabric panel. C3,C5는 해당 영상의 좌·우 teeth/tape. 이 좌우를 실제 물리 방향으로 주장하지 않는다. 각 ROI는 native reference 이미지/SHA에 근거한다.
- 다른28품목: 기존 등록 주요 부위로 공간 계산은 구현. 의미 있는 하위 부위/정밀 물리 표면 검증은 PARTIAL. 균일 격자는 통계 격자이며 의미적 하위 부위가 아니다.

현재30품목 상태:

| 품목 | 등록 시점 | 미등록 시점 | 표본 제품 |
|---|---|---|---|
| audiojack | C1,C2,C3,C4,C5 | 없음 | 2 |
| bottle_cap | C1,C2,C3 | C4,C5 | 2 |
| button_battery | C1,C2,C3 | C4,C5 | 2 |
| end_cap | C1,C2,C3 | C4,C5 | 2 |
| eraser | C1,C2,C3 | C4,C5 | 2 |
| fire_hood | C1,C2 | C3,C4,C5 | 2 |
| mint | C1,C2 | C3,C4,C5 | 2 |
| mounts | C1,C2 | C3,C4,C5 | 2 |
| pcb | C1,C2 | C3,C4,C5 | 2 |
| phone_battery | C1,C2 | C3,C4,C5 | 2 |
| plastic_nut | C1,C2 | C3,C4,C5 | 2 |
| plastic_plug | C1 | C2,C3,C4,C5 | 2 |
| porcelain_doll | C1,C2 | C3,C4,C5 | 2 |
| regulator | C1,C2 | C3,C4,C5 | 2 |
| rolled_strip_base | C1,C2 | C3,C4,C5 | 2 |
| sim_card_set | C1,C2 | C3,C4,C5 | 2 |
| switch | C1,C2 | C3,C4,C5 | 2 |
| tape | C1,C2 | C3,C4,C5 | 2 |
| terminalblock | C1,C2 | C3,C4,C5 | 2 |
| toothbrush | C1,C2,C3,C4,C5 | 없음 | 2 |
| toy | C1,C2 | C3,C4,C5 | 2 |
| toy_brick | C1,C2 | C3,C4,C5 | 2 |
| transistor1 | C1,C2 | C3,C4,C5 | 2 |
| u_block | C1,C2 | C3,C4,C5 | 2 |
| usb | C1,C2 | C3,C4,C5 | 2 |
| usb_adaptor | C1,C2 | C3,C4,C5 | 2 |
| vcpill | C1,C2 | C3,C4,C5 | 2 |
| wooden_beads | C1,C2 | C3,C4,C5 | 2 |
| woodstick | C1,C2 | C3,C4,C5 | 2 |
| zipper | C1,C2,C3,C4,C5 | 없음 | 2 |

기계 판독: `reports/spatial_heatmap/roi_spatial_status.csv`. 72등록/78미등록 조합. 미등록은 촬영 불가능 판정이 아니라 아직 ROI가 등록되지 않은 상태다. 실제150이미지 survey의 표시를 검토했다. 다른제품에 template 적용 시 자세 정합은 보증하지 않으며 개별 원본 오버레이로만 제공한다.

추가 실제 검토: `reports/spatial_heatmap/primary-hierarchical-roi-overlay.jpg`에서 칫솔·지퍼 C1–C5의 부모/자식 경계를 직접 확인했다. 지퍼의 영상상 상하/좌우 구분이 금속열·직물에 대응하며, 굴곡진 금속 끝의 일부는 폴리곤 밖으로 남는다. ROI 외부를 강제 배정하지 않는다. 칫솔 C1의 끝/중앙/기저 구간은 영상 기반 구간이며 C2–C5에 이를 회전 복제하지 않았다. 이 이미지는 브라우저 캡처가 아니다. 재생성: `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/review_spatial_data.py`.
