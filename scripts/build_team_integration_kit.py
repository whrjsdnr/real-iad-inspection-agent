"""Build an allowlisted, secret-scanned development ZIP from verified read APIs."""
import asyncio,json,zipfile
from pathlib import Path
from app.shared_data_api import clean,parts_catalog,roi_config
from app.team_api import shared_openapi
ROOT=Path(__file__).resolve().parents[1];KIT=ROOT/'team_integration_kit'
KIT.mkdir(exist_ok=True)

def write(name,value):
    path=KIT/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(clean(value),ensure_ascii=False,indent=2)+'\n' if not isinstance(value,str) else value.strip()+'\n')

write('ROI_CATALOG.json',{'legacy':roi_config(),'spatial_hierarchy':json.loads((ROOT/'config/spatial_regions.json').read_text()),
 'scope_note':'69 existing native-image templates; spatial hierarchy adds selected reference-view definitions. No calibrated physical UV atlas.'})
write('PARTS_CATALOG.json',parts_catalog())
write('openapi.json',asyncio.run(shared_openapi()))
for path in (KIT/'samples').glob('*.json'):write(str(path.relative_to(KIT)),json.loads(path.read_text()))
write('README.md','''# 검사 데이터 공동 개발 패키지

실제 저장된 30품목/24,000제품/120,000시점을 팀 GUI·에이전트가 공통으로 읽기 위한 패키지다. DB 계정이나 DB 접속 없이 API만 사용한다. 검수 확정 통계, 원시 모델 신호, 보고서 전용 퓨전 결과는 서로 구분한다.

현재 검증: 실제 접속키 인증을 포함한 ASGI HTTP 라우팅·실데이터 조회 통과. 2026-11-25 기준 개발 읽기전용 게이트웨이(127.0.0.1:18080)에서 공유 API 전부 실응답 확인(새 코드 기동). 운영 중앙 서버(:8000)는 아직 구 코드라 /products·/fusion/runs·/heatmaps·/sharing/kit이 404다 — 배포 재시작은 담당자 승인 후 수행. 호스트 LAN IP는 172.24.157.10이며 18081 팀 공유 서비스 가동 시 해당 주소로 접근. samples는 실제 호출 응답이며 Mock이 아니다. 신규코드가 현재 운영 프로세스에 로드됐다고 보증하지 않는다.

## 호스트 담당자

기존 중앙 서버가 이번 소스를 배포했으면 기존 API 기본주소를 사용한다. 운영 재시작은 이번 작업에서 실행하지 않았다. 중앙 서버를 건드리지 않는 별도 공유 서비스도 준비돼 있다:

```bash
cd /home/geonug/agent
.venv/bin/python scripts/setup_team_share.py
TEAM_BIND_HOST=0.0.0.0 TEAM_SHARE_PORT=18081 nohup bash scripts/start_team_share.sh > reports/gui_validation/spatial-urgent/team-host.log 2>&1 &
```

팀원에게 실제 호스트 LAN/VPN 주소와 TEAM_ACCESS_TOKEN 값만 별도 전달한다. config/team-share.env 전체와 DB URL은 공유하지 않는다. 필요시 TEAM_ALLOWED_ORIGINS에 팀 GUI 출처를 쉼표로 지정한다. 기본값은 http://localhost:5173,http://127.0.0.1:5173 이다. 공용인터넷 주소를 새로 열거나 DB 포트를 공개하지 않았다.

## 팀원 4명

각자 로컬 GUI/에이전트에서 같은 기본주소를 사용한다. API 주소 예시는 `http://<호스트 LAN/VPN IP>:18081/api`이며 이 IP는 아직 실측·검증되지 않았다. 접속키는 Bearer 헤더로 전송한다. 공유키 방식이며 개인별 계정·검수쓰기 기능은 아니다.

```bash
export TEAM_API_URL='http://<실제 서버 IP>:18081/api'
# TEAM_ACCESS_TOKEN을 비공개 환경변수로 설정한 뒤 실행한다. 값은 커밋하지 않는다.
python examples/python_client.py
```

본 패키지에는 모델 가중치·전체 원본 이미지·전체 DB가 없다. 예제 응답, ROI/부위 정의, OpenAPI가 포함된다. 원본/NPY는 API로 읽는다. 실제 공간 배열을 3D 모델 표면에 표시하는 근사 투영 런타임을 포함한다. 물리 좌표의 실측 정합을 뜻하지 않는다.
''')
write('API_GUIDE.md','''# API 사용법

공유 게이트웨이 기본주소는 `http://<HOST-IP>:18081/api`. 모든 요청에 `Authorization: Bearer <TEAM_ACCESS_TOKEN>`을 넣는다. URL이나 소스 코드에 실제 키를 넣지 않는다. 기존 중앙 API의 root 주소에는 `/api` 프리픽스가 없을 수 있으므로 운영자 설정을 따른다. GUI는 상대 `/api`를 사용한다. 현재15173 개발 서버의 MV/표면 조회는 읽기 전용 bridge이며 나머지 기존 프록시는18080이다. 운영8000/8080 실제 listen 상태와 외부 연결은 이번 환경에서 확인하지 못했다.

| 조회 | 경로 | 범위/주의 |
|---|---|---|
| 데이터·계약·30품목 목록 | GET /sharing/manifest | 실제 저장 cohort 캐시. 기존 GET /items는 운영DB 품목 목록이며 네트워크 미검증 |
| 부위 ID | GET /catalog/parts?item=toothbrush | 메시 ID와 계층형 ROI ID, 관측 시점, UV 미검증 |
| ROI | GET /roi/templates?item=toothbrush&view=C1 | 기존69 native 템플릿, offset/limit≤100 |
| ROI 품목별 | GET /roi/templates/toothbrush | 같은 API의 품목별 별칭 |
| 세부 ROI | GET /roi/hierarchy?item=toothbrush | spatial_regions의 별도 버전 |
| 제품 목록 | GET /products?item=toothbrush&limit=50&offset=0 | 최대100, product_id/status 필터 |
| C1–C5/점수/좌표 | GET /products/views?product_id=...&view=C1 | 제품 ID에 /가 있으므로 query parameter 사용 |
| 저장박스 | GET /products/findings?product_id=...&view=C1&model=rt&min_confidence=0.4 | bbox XYXY, confidence, class, ROI; offset/limit≤500 |
| 실제 원본 | GET /products/image?product_id=...&view=C1 | 허용 dataset root 안의 저장 파일만 |
| 표시용 3D 공간 배열 | GET /heatmaps/surface?item=toothbrush&view=C1&source=hvq | 같은 대표 제품 RT/HVQ; 실제 배열/투영 설정 |
| 지원 표면 모드 | GET /heatmaps/surface-layout?item=toothbrush | 3종 데이터/시점/지원 여부 |
| 실제 이상 맵 | GET /products/anomaly-map?product_id=...&view=C1&format=metadata | format=array 또는 npy; 없으면 unsupported |
| 기존 부위 통계 | GET /parts/heatmap?item=toothbrush | 기존 계약 유지; 검출 의심 신호와 확정 검수 지표 구분 |
| 실제 공간 배열 | GET /parts/spatial-heatmap?item=toothbrush&product_id=toothbrush/NG/CH/S0001&view=C1&region_id=bristle&model=rt&resolution=32&method=confidence_area | 원시박스 좌표 집계; 개별 제품/단일카메라 |
| 공간 캐시 목록 | GET /parts/spatial/index?item=toothbrush | 실제 지원 제품/시점/부위만 선택 |
| 퓨전 보고서 판정 | GET /products/fusion?product_id=... | report_only, 운영 판정을 대체하지 않음 |
| 기존 평가 보고 | GET /performance/final | 기존 평가 API 재사용 |
| 도구 | GET /tools, POST /tools/{tool_name} | 읽기 허용목록만; query_spatial_evidence 포함 |
| 명세 | GET /openapi.json | 실제 공유 서비스 스키마, Bearer 인증 |

RT/HVQ 공간 모드는 실제 저장 자료만 조회한다. model_version별 전수 공간 집계/카메라 보정/검수 위치 FP·FN은 미지원이다. API는 지원하지 않는 모델 타입과 해상도를 거부한다. ZIP의 OpenAPI는 현재 소스의 준비된 API이며 배포 완료 증거가 아니다.

예제 URL의 product_id는 반드시 URLSearchParams/urlencode로 인코딩한다. 데이터 양이 크면 페이지네이션을 사용한다. NPY 원시 맵은 numpy.load(...,allow_pickle=False)로 읽는다. 401=키/로그인,404=없는 제품/캐시,409=원본·설정 불일치,422=입력 오류,503=저장 캐시 없음이다.
''')
write('DATA_DICTIONARY.md','''# 공통 데이터 정의

제품 = 동일 product_id의 C1–C5 묶음. 제품수와 박스수는 다르다. source=`saved_batch5_score_cache`는 기존 읽기전용 SQLite 결과 사본이며 현재 운영PG의 active run과 동일 정책이라고 가정하지 않는다. 제품 split/truth는 저장된 라벨이며 분할을 변경하지 않는다.

- bbox: 원본 픽셀 XYXY, width/height는 원본 해상도. confidence는 저장된 RT-DETR 신뢰도. /products/findings는 기본적으로 저장 박스를 모두 반환하며 min_confidence로 선택한다. RT 공간 시각화의 선택값은 기존 계약0.4다.
- views.hvq/제품 hvq_max: 저장 컬럼 원시값. 칫솔 GUI 일치표본에서 heatmap_mean과 일치함을 확인했으나 전 코호트 컬럼 출처를 별도 재추론해 검증하지 않았다. API가 이 provenance 한계를 표시한다. 정규화/공식 퓨전 입력과 임의 혼용하지 않는다.
- anomaly_map: 실제 저장224² NPY가 확인되고 원본 SHA가 일치할 때만 supported. 실제 저장500맵/100제품/30품목에서 지원한다. 상대경로는 점수캐시 디렉터리를 기준으로 복원한다. /products?maps_only=true로 지원 참조 제품을 찾고 개별 맵 API에서 검증한다. 스칼라로 대체하지 않는다.
- 좌표: RT 원본 복원은 inference.py postprocess(orig_sizes) 코드 경로를 확인했다. 입력코드의 direct Resize와 달리 모든 저장행에 crop/pad 행렬 메타데이터가 있는 것은 아니다. per_record_transform_metadata=null은 미저장 상태다. 실제 맵 표본은 확인된 full-frame direct resize를 사용한다. legacy640×480 LUT를 일괄 확대하지 않는다.
- region_id: 기존 메시 ID를 유지한다. ROI child ID는 parent_region_id로 연결된다. 지원 시점은 영상 ROI 정의를 뜻하며 보정된 표면 가시성 mask가 아니다. UV 정합과 카메라 extrinsics는 미확인이다.
- /products/fusion: 공식 저장 평가 CSV의 report_only 판정과 수치. database_run_activated=false. 운영 기존 verdict를 수정하지 않는다. 평가설정 version은 weighted-minmax-heatmap-mean-rt40-v1이며 사용자 지칭 퓨전 계약v2의 설정이다. RT0.7/HVQ0.3, 카테고리별 Val minmax, heatmap_mean·RT0.4, max_C1_C5, Val F1 최적 TH와 허용하락0.005 margin. 세부값은 응답과 기존 평가 보고서에 보존한다.
- 98.84%는 과거 사용자가 보고한 수치다. 지표 정의가 불명확한 상태에서 현재 저장 평가 결과로 덮어쓰거나 같은 평가라고 주장하지 않는다.

검수 전 신호는 의심 건수/검출 위치로 해석한다. 확정 불량률·FP·FN·미탐 위치는 검수/GT 위치 근거 없이 계산하지 않는다. 기존 부위 운영집계의 분모24,001과 공식 코호트24,000은 동일 범위로 검증된 값이 아니다. 현재 카메라/기간/모델 필터의 기존 artifact 적용 범위는 별도 점검 항목이며 공간 개별제품 API와 구분한다.
''')
write('HEATMAP_GUIDE.md','''# 공간 히트맵 계산과 표시

기존 부위별 API는 rate 한 값으로 전체 부위를 칠한다. 공간 API는 실제 saved Bounding Box를 ROI 내부 좌표로 정규화하여 32×32 격자에 누적한다. 예제 실제 칫솔 C1은 2박스,1,024셀 중174개 양의 신호,19종 값이다. 검출 중심은 (17,7),(26,26)셀에 연결된다.

values/observation_counts/coverage_mask는 row-major(y 아래 방향) 길이 width×height 배열이고 values_2d는 같은 배열의 행 표현이다. center_counts, box_occupancy_counts, detected_product_counts, confidence_weighted_area, mean_confidence를 따로 제공한다. 같은 박스의 정확중복을 제거하며 동일제품의 박스들을 여러제품으로 세지 않는다. 서로 다른 카메라의 좌표를 합치지 않는다. 부모/자식 지도를 합산하지 않는다.

RT method: center_count,box_area,confidence_area,gaussian,product_occupancy,mean_confidence. Gaussian은 박스중심 분포 시각화이며 실제 결함 마스크가 아니다. 박스 내부 전체를 실제 불량 영역으로 간주하지 않는다. HVQ mean/max/percentile은 실제 원시 맵 표본을 집계하고 비어 있는 고해상도 bin을 보간으로 채우지 않는다.

유효분모는 해당 제품·시점의 등록 ROI envelope 안 영상 관측1이며 카메라 보정으로 확인된3D 표면 관측수가 아니다. rate_supported=false이므로 발생률/확정 불량률로 표시하지 않는다. 표본1은 MIN_DENOMINATOR10 미만으로 별도 표기한다. 미검출0,미관측null,표본부족,미지원은 구분한다. 관측되지 않은 셀은 투명하게, 검출0은 낮은 신호로 표시하되 정상 판정이라고 쓰지 않는다.

현재 표시 방식은 사용자가 승인한 근사 표면 투영이다. 기존 primitive UV를 사용하지 않고 부위 전체에 연속적인 투영 UV를 새로 만든다. DataTexture/ShaderMaterial이 실제 메시 표면에 붙으며 칫솔모 측면도 위치별 히트맵 색을 따른다. 실제 수치는 유지하고 유효 관측 범위 안에서만 색을 부드럽게 보간한다. 물리 좌표 실측이 아니므로 physical_alignment_verified는 false다. 공유 런타임과 적용 예제는 THREE_SURFACE_GUIDE.md를 참고한다.

공간 캐시는 대표제품에 한정된다. 전수24,000개를 공간적으로 정합해 집계한 결과가 아니다. 동일품목/다른제품 자세 정합도 검증하지 않았다. 16/32/64/128은 표시·집계 해상도이며 원본 측정 정확도를 높이지 않는다. 상세 원본 근거와 공급 범위는 API 응답을 우선한다.
''')
write('QUICKSTART.md','''# 퀵스타트 — 5분 안에 첫 조회

이 패키지는 DB 계정 없이 HTTP API만으로 실제 30품목/24,000제품/120,000시점 데이터를 읽기 위한 것이다. ZIP 안에 모델 가중치·전체 이미지·DB가 없다.

## 0. 준비

팀 API 주소와 접속키를 담당자에게 받는다. 키는 환경변수로만 설정하고 소스/커밋에 넣지 않는다.

```bash
export TEAM_API_URL='http://<호스트 IP>:18081/api'   # 또는 운영자가 지정한 주소
export TEAM_ACCESS_TOKEN='<담당자가 별도 전달>'
```

## 1. API만 쓰는 팀원(1분)

```bash
python examples/python_client.py        # manifest → 제품 목록 → 실제 32² 공간 배열
```

## 2. 3D 표면 SDK만 쓰는 팀원

three_surface/ 런타임과 THREE_SURFACE_GUIDE.md를 본다. 로컬 Three.js 프로젝트에 모듈을 복사하고 surface_frames/의 실제 32² 배열과 투영 설정을 그대로 적용한다. npm 설치가 필요한 공유 런타임 의존성은 three 뿐이다.

## 3. GUI/에이전트 팀원

GUI는 상대 경로 /api를 쓰고 Vite 프록시로 연결된다. 새 에이전트 도구는 OpenAPI(openapi.json) 스키마와 /tools 응답을 기준으로 만든다. 실제 호출 예시는 samples/*.json이며 이것은 실제 API 응답 사본이다.

## 4. 바로 확인할 것

1. GET /sharing/manifest → 품목 수/제품 수/시점 수(30/24000/120000 기대)
2. GET /products?item=toothbrush&limit=2 → 실제 제품 ID(C1–C5 묶음)
3. GET /products/findings?product_id=...&view=C1 → 저장된 RT-DETR 박스
4. GET /heatmaps/ground-truth?item=toothbrush&view=C1 → 실제 마스크 64×64 수치 배열

자주 발생하는 오류: 401=키 누락/불일치, 404=존재하지 않는 제품·경로(또는 서버가 구 코드), 422=파라미터 오류, 503=저장 캐시 없음. 자세한 표는 API_GUIDE.md, 필드 정의는 DATA_DICTIONARY.md.
''')
write('FUSION_CONTRACT.md','''# 퓨전 계약(확정 v2)

평가 설정 버전: `weighted-minmax-heatmap-mean-rt40-v1`. 저장된 120,000시점 점수 재사용(재추론 없음)으로 산출한 계약이다.

## 규칙

1. 제품 = 동일 product_id의 C1–C5 정확히 5개. 각 모델 제품 점수는 5시점 최댓값.
2. RT-DETR은 저장 최대 신뢰도가 0.4 미만이면 0. HVQ-Trans는 연속 heatmap_mean 점수를 사용하고 max16용 임계값은 쓰지 않는다.
3. 정규화: Validation 3,610제품에서 품목별·모델별 min/max 산출 후 `(점수−min)/(max−min)`. 상수 범위는 거부. Val 범위 밖은 수식대로 외삽(확률로 해석 금지).
4. 제품 fusion_score = 0.7×RT_norm + 0.3×HVQ_norm. 모델별 지표 가중 평균 금지.
5. 품목별 TH = Validation F1 최대 구간 중 가장 높은 구간의 중점. margin = 정점 대비 F1 하락 0.005 이내 연결 구간. `abs(score−TH) ≤ margin`이면 보류.
6. 모든 보정은 Validation에서만 산출하고 Test/운영에는 고정 적용.

## 결과(저장 점수 재평가)

| 범위 | 제품 | Recall | F1 | FP/FN | AUROC | 보류 |
|---|---:|---|---|---|---|---:|
| 전체 참고(Val 포함) | 24,000 | 12,102/12,408 = 97.5338% | 0.968780 | 474/306 | 0.992895 | 194 |
| Test(학습·검증 제외) | 3,593 | 1,752/1,838 = 95.3210% | 0.953210 | 86/86 | 0.986346 | 37 |

전체 집계는 Validation을 포함한다. 전체 24,000제품은 두 비전 모델(RT-DETRv2·HVQ-Trans)의 학습에 사용되지 않았다(훈련 담당자 확인). 단, 정규화/TH/margin 보정은 이 데이터의 Validation 3,610에서만 이뤄졌으므로 전체 지표에는 규칙 보정 데이터가 포함된다. 완전 홀드아웃인 별도 Test가 대표 지표다.

## 이전 계약과의 비교(동일 평가 범위)

| 규칙 | Test F1 | Test Recall | 전체 F1 |
|---|---:|---:|---:|
| 구 max16/백분위/RT0.55 | 0.942795 | 95.0490%(1,713/1,801 대상 정의 상이) | 0.959035 |
| 현재 v2(위 규칙) | 0.953210 | 95.3210% | 0.968780 |

과거에 보고된 98.84%는 평가 원본이 확인되지 않아 대표 성능으로 쓰지 않는다.

## 운영 반영 상태

- 평가 산출물(reports/final_performance_minmax/)은 `report_only` 계약이며 운영 DB의 기존 max16 판정을 덮어쓰지 않는다.
- DB fusion_analysis.model_runs에는 v2 run(`weighted-minmax-heatmap-mean-rt40-v1:e917f9730ddb05d9c486b45d`)이 활성(is_active)으로 등록됐고 구 max16 run은 보존·비활성이다. 조회 API /fusion/runs가 둘을 모두 보여준다.
- /products/fusion 은 저장 평가 CSV(report_only)의 판정을 반환한다. 운영 서버 프로세스가 구 코드면 /fusion/runs·/products 등 공유 API 자체가 404일 수 있다(배포 상태는 담당자 확인).
''')
write('DATA_AVAILABILITY.md','''# 데이터 가용성 — 무엇이 어디에 있는가

| 데이터 | 범위 | 제공 방식 | 비고 |
|---|---|---|---|
| 제품/시점 코호트 | 24,000제품·120,000시점(C1–C5) | API /products·/sharing/manifest | split train 16,797/val 3,610/test 3,593. 두 비전 모델 학습 미사용(훈련 담당자 확인) |
| RT-DETR 박스·신뢰도 | 전체 저장 시점 | API /products/findings | 원본 픽셀 XYXY |
| HVQ 이상 점수 | 전체 저장 시점(스칼라) | API /products/views | heatmap_mean 출처 일치는 칫솔 표본에서 확인, 전 코호트는 미재검증 |
| HVQ 원시 Anomaly Map | 500개 시점·100제품·30품목뿐 | API /products/anomaly-map | 224×224 NPY. 전체 제품에 맵이 있는 것은 아님. 없으면 unsupported |
| 불량 마스크 64×64 수치 배열 | 30품목×5시점 = 150개 | API /heatmaps/*, heatmaps/*.json | Train NG 기반 집계. 정상/Test는 분모에서 제외 |
| RT/HVQ 공간 대표 배열 | 같은 대표 제품 300개 응답 | API /heatmaps/surface, surface_frames/ | 개별 제품·단일 칩첩; 전수 공간 집계 아님 |
| ROI/부위 정의 | 기존 69 템플릿+계층 ROI | /roi/templates, ROI_CATALOG.json | 원본 픽셀 좌표 폴리곤. UV/칙첩 보정 미검증 |
| 부위별 관측 분모/양성 | 기존 계약 집계 | /parts/heatmap | 분모 24,001은 공식 코호트 24,000과 동일 범위로 검증된 값 아님 |
| 퓨전 평가 결과 | 위 FUSION_CONTRACT.md 표 | /products/fusion, /performance/final | report_only 저장 평가 |
| ZIP에 없는 것 | 모델 가중치, 전체 원본 이미지, 전체 DB, 전수 원시 맵 | — | 필요시 담당자 승인 하에 별도 제공 |

데이터가 없는 경우의 처리: API는 없는 맵/캐시를 지원한다고 거짓 응답하지 않는다. unsupported/404/503을 받으면 스칼라로 대체하거나 가상 핫스팟을 만들지 말고 "데이터 없음"으로 표시한다. 소표본(분모 MIN_DENOMINATOR 미만)은 수치 대신 사유를 표시한다.
''')
write('examples/python_client.py','''"""Standard-library read client. Set TEAM_API_URL and private TEAM_ACCESS_TOKEN."""
import json,os
from urllib.parse import urlencode
from urllib.request import Request,urlopen

class InspectionClient:
    def __init__(self,base_url,token):self.base_url=base_url.rstrip('/');self.token=token
    def get(self,path,**params):
        url=self.base_url+path+('?' + urlencode(params) if params else '')
        request=Request(url,headers={'Authorization':'Bearer '+self.token})
        with urlopen(request,timeout=15) as response:return json.load(response)

if __name__=='__main__':
    client=InspectionClient(os.environ['TEAM_API_URL'],os.environ['TEAM_ACCESS_TOKEN'])
    manifest=client.get('/sharing/manifest')
    print('items',len(manifest['items']),'products',manifest['products'],'views',manifest['views'])
    rows=client.get('/products',item='toothbrush',limit=2)
    print('products returned',len(rows['products']))
    grid=client.get('/parts/spatial-heatmap',item='toothbrush',product_id='toothbrush/NG/CH/S0001',view='C1',region_id='bristle',model='rt',resolution=32,method='confidence_area')
    assert grid['grid_width']==grid['grid_height']==32 and len(grid['values'])==1024
    print('spatial grid',grid['grid_width'],grid['grid_height'],'distinct values',len(set(grid['values'])))
''')
write('examples/typescript_client.ts','''/** Supply the API base URL and token at runtime; never commit real credentials. */
export interface SpatialGrid {
  item:string;product_id:string;region_id:string;view:string;model:'rt'|'hvq';
  grid_width:number;grid_height:number;values:(number|null)[];values_2d:(number|null)[][];
  observation_counts:number[];coverage_mask:number[];mapping_status:string;
  mapping_version:string;source:string;rate_supported:boolean;
}
export class InspectionClient {
  constructor(private baseUrl:string,private token:string){}
  async get<T>(path:string,params:Record<string,string|number>={}):Promise<T>{
    const query=new URLSearchParams(Object.entries(params).map(([key,value])=>[key,String(value)]));
    const response=await fetch(this.baseUrl.replace(/\\/$/,'')+path+'?'+query,{
      headers:{Authorization:'Bearer '+this.token},credentials:'omit',signal:AbortSignal.timeout(15000)});
    if(!response.ok)throw new Error(`Inspection API ${response.status}`);
    return await response.json() as T;
  }
  toothbrushGrid(){return this.get<SpatialGrid>('/parts/spatial-heatmap',{
    item:'toothbrush',product_id:'toothbrush/NG/CH/S0001',view:'C1',region_id:'bristle',model:'rt',resolution:32,method:'confidence_area'});}
}
''')
# Preserve the independently exported MV arrays, guide and guarded Three example.
client=KIT/'examples/python_client.py'
client.write_text(client.read_text()+"\n\ndef ground_truth(client,item='toothbrush',view='C1'):\n    return client.get('/heatmaps/ground-truth',item=item,view=view,split='train')\n")
client=KIT/'examples/typescript_client.ts'
client.write_text(client.read_text()+"\nexport function preservedTrainMask(client:InspectionClient,item='toothbrush',view='C1'){\n  return client.get('/heatmaps/ground-truth',{item,view,split:'train'});\n}\n")
for guide in ['README.md','API_GUIDE.md','HEATMAP_GUIDE.md']:
    path=KIT/guide;path.write_text(path.read_text()+'\n기존 MV 마스크 기반150개 64×64 수치도 포함합니다. MV_HEATMAP_REUSE.md와 HEATMAP_CATALOG.json, heatmaps/*.json을 확인하세요. 마스크 API는 /heatmaps/catalog, /heatmaps/ground-truth, /heatmaps/metadata입니다.\n')
# Allowlisted file types only. No recursive blind archive of the repository.
files=[path for path in KIT.rglob('*') if path.is_file() and path.suffix in ('.md','.json','.py','.ts','.csv','.mjs','.mts','.css')]
for path in files:
    if any(part.startswith('.') for part in path.relative_to(KIT).parts):raise ValueError('Hidden file in kit')
    text=path.read_text()
    if any(value in text for value in ('postgresql://','postgresql+psycopg2://','PRIVATE KEY-----')):raise ValueError('Sensitive source in kit: '+path.name)
private=ROOT/'config/team-share.env'
if private.exists():
    secrets=[line.partition('=')[2] for line in private.read_text().splitlines() if line.startswith(('TEAM_ACCESS_TOKEN=','DATABASE_URL_READ='))]
    for path in files:
        if any(secret and secret in path.read_text() for secret in secrets):raise ValueError('Private credential in kit')
archive=ROOT/'team_integration_kit.zip'
temporary_archive=archive.with_suffix('.tmp.zip')
with zipfile.ZipFile(temporary_archive,'w',compression=zipfile.ZIP_DEFLATED) as package:
    for path in files:package.write(path,Path('team_integration_kit')/path.relative_to(KIT))
temporary_archive.replace(archive)
print(json.dumps({'archive':str(archive),'files':len(files),'bytes':archive.stat().st_size,'secret_scan':'passed'}))
