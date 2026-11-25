> 2026-11-25 최신: MV_HEATMAP_REUSE_REPORT.md / MV_MASK_API_404_FIX_REPORT.md / TEAM_DATA_SHARING_REPORT.md / FUSION_POLICY_COMPARISON.md 우선. 현재2D실데이터/공유API는구현·수치검증, 3D물리표면투영과호스트브라우저는미완료. 최신Python128/프런트131통과.

# 표면 매핑 검증

상태: 영상좌표 공간지도 IMPLEMENTED / 실제 원본오버레이 VERIFIED / 물리3D투영 미지원.

A. 세부메시색: 적은자원, 의미적부위 단위이며 연속공간 표현이 제한된다. 영상과 메시 하위부위 대응을 먼저 검증해야 한다.
B. UV DataTexture: 연속분포를 표현하지만 현재 primitive UV가 반복·중첩돼 native ROI의 물리좌표 대응이 없다. 검증된 mapping_version/geometryVersion일 때만 DataTexture를 생성하는 guard와 dispose 테스트를 구현했다. 현재실제데이터에 이를 활성화하지 않았다.
C. VertexColor: 추가텍스처가 필요없지만 메시밀도에 따라 신호가 퍼지며 표면대응 근거가 여전히 필요하다. 현행프로젝트에 임의 vertex색을 적용하지 않았다.

현재 GUI는 기존3D 주요부위색과 회전/선택을 유지하고, 신규 세부공간은 시점별2D 원본 위에 보여준다. 이는 사용자 지시의 검증되지 않은3D대응에 대한 fallback이다. 메시 밖으로 임의신호를 투영하지 않는다. 카메라회전에 따라3D표면의 국소 hotspot이 유지된다고 주장할 수 없다.

실제원본 칫솔/지퍼와 ROI/박스 오버레이, survey6장을 도구로 열어 검토했다. 칫솔은 헤드확대이며 손잡이를 유추하지 않았다. 지퍼 C1–C5의 금속열과 직물영역을 영상방향별로 나눴다. 제품별자세/가림/3DUV 보정은 미확인이므로 전체제품군 공간정합으로 확대하지 않는다.

근거: reports/spatial_heatmap/primary-spatial-comparison.jpg, roi-survey-01.jpg~06.jpg, config/spatial_regions.json. 라이브브라우저 스크린샷이 아니다.

추가 실제 검토: `reports/spatial_heatmap/primary-hierarchical-roi-overlay.jpg`에서 칫솔·지퍼 C1–C5의 부모/자식 경계를 직접 확인했다. 지퍼의 영상상 상하/좌우 구분이 금속열·직물에 대응하며, 굴곡진 금속 끝의 일부는 폴리곤 밖으로 남는다. ROI 외부를 강제 배정하지 않는다. 칫솔 C1의 끝/중앙/기저 구간은 영상 기반 구간이며 C2–C5에 이를 회전 복제하지 않았다. 이 이미지는 브라우저 캡처가 아니다. 재생성: `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/review_spatial_data.py`.
