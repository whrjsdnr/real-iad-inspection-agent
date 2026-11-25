# 퀵스타트 — 5분 안에 첫 조회

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
