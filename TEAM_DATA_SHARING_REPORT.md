# 검사·ROI·공간 데이터 공유 결과 — 2026-11-25

IMPLEMENTED: 기존 중앙/readonly router에 읽기전용 shared_data_api와 ground_truth_api를 등록. 기존 /items,/tools,/parts/heatmap,/parts/spatial-heatmap,/performance/final은 재사용한다. 제품목록/시점/박스/원본/실제NPY/보고서퓨전, ROI와부위카탈로그, MV마스크수치가 부족한항목으로 추가됐다.

VERIFIED: 실제 접속키를 사용하는 인증된ASGI HTTP조회21건. 30품목24,000제품120,000시점 캐시, 원본박스·실제224²NPY배열·69ROI·64²GT·32²RT·기존평가를 조회했다. unauthenticated401,추론POST미등록,검수쓰기거부,CORS preflight를검사했다. 신규캐시DB연결은 mode=ro/query_only로 강제하고 쓰기거부를 단위검사했다.

API: /sharing/manifest,/catalog/parts,/roi/templates,/roi/templates/{item},/roi/hierarchy,/products,/products/views,/products/findings,/products/image,/products/anomaly-map,/products/fusion,/heatmaps/catalog,/heatmaps/ground-truth,/heatmaps/metadata,/heatmaps/evidence. 제품ID의슬래시때문에 query parameter를 사용한다. 목록최대100,박스최대500 페이지네이션. 고정저장결과와보고서전용퓨전은 운영DB active run과출처를구분한다. 검수없는FP/FN공간위치는생성하지않는다.

공유용 team_api는 기존read계정·별도서비스18081·Bearer 또는8시간서명cookie·허용출처CORS를사용한다. DB계정/스키마/권한변경과운영재시작은하지않았다. config/team-share.env는권한600이며패키지에포함하지않는다. 팀원은접속키만별도전달받는다.

공유패키지: team_integration_kit.zip. 150개품목/시점별TrainNG수치,API실응답,OpenAPI,ROI/메시부위정의,사용법,Python/TypeScript/Three예제. 실제키/DB URL과숨김파일이없는지검사했다. Three표면적용예제는검증된binding이없으면거부하며현재3D완료증거가아니다.

네트워크상태: 사용자확인GUI http://127.0.0.1:15173/#/dashboard. 해당 /api/heatmaps/* 개발연결수정과 실제reader검사를통과했으나 호스트TCP/8000·8080 actual listen·실행uvicorn명령·외부팀원IP는 sandbox socket EPERM/호스트PID비가시성으로미검증이다. 팀원중앙주소를임의생성하지않는다. 최신소스를기존서버에배포하거나별도인증공유서비스를호스트에서실행한뒤 LAN/VPN IP:18081/api를검증해야한다.

검증기록: reports/gui_validation/spatial-urgent/team-data-validation.json 및 vite-mv-bridge-validation.json. Python128통과4skip,프런트131통과,lint/TS/build통과. 현재퓨전은동일코호트비교에서더높아유지하기로사용자확정했다(FUSION_POLICY_COMPARISON.md).
