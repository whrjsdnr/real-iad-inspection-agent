# 15173 개발 GUI의 MV API 404 연결 수정

사용자가 확인한 화면: http://127.0.0.1:15173/#/dashboard

기존 실행 스크립트는15173 Vite → /api 프록시 → 읽기전용18080으로 연결한다. 수치 캐시는 존재하지만 이 실행 중인 API가 신규 라우터를 읽지 않은 경우 catalog가404가 된다. 현재 소스의 중앙/readonly/preview OpenAPI에는 heatmaps 경로가 모두 등록돼 있다. 실제 운영8000/8080 PID·명령·Network 응답 본문은 sandbox 제약으로 확인하지 못했다.

Vite 개발 전용 mvApiBridge.mjs를 연결해 GET /api/heatmaps/{catalog,ground-truth,metadata,evidence}와 비교용 /api/products/findings만 기존 Python FastAPI 로더로 전달한다. 계산/응답 정의를 복제하거나 Mock으로 대체하지 않는다. 다른 API 요청은 원래 프록시를 유지한다. 중앙FastAPI/18080/DB동기화/모델프로세스를 재시작하지 않는다. 로컬 reader만 최대2개·큐16개로 제한한다.

Vite config 자동 재적용 후 Ctrl+Shift+R로 화면을 새로고침한다. Network 응답의 X-MV-Transport: vite-local-existing-asgi-routes를 확인한다. 아래는 사용자 화면과 같은 PC에서의 개발 조회 주소이며, 외부 팀원PC에서127.0.0.1로 접속하면 그 팀원 자신의 PC를 뜻한다.

- http://127.0.0.1:15173/api/heatmaps/catalog?item=toothbrush
- http://127.0.0.1:15173/api/heatmaps/ground-truth?item=toothbrush&view=C1&split=train
- http://127.0.0.1:15173/api/heatmaps/ground-truth?item=zipper&view=C1&split=train

실제 middleware + Python loader 검사: 칫솔200/64²/known335/unknown37/서로다른값35종, 지퍼200/64²/known367/unknown0/값112종. 원본JPEG 전달도 각각348,330/562,978 bytes를 확인했다. HTTP 소켓을 사용하지 않은 연결 통합검사이며, 실제 브라우저/TCP까지 검증한 것은 아니다.

중앙 팀공유 주소는 최신 FastAPI 소스를 승인된 방식으로 반영한 후 기존 중앙주소 또는 별도 인증공유18081/api를 사용한다. 현재 실제 외부IP·접속성은 미확인이다. 이 Vite 개발용 경로가 중앙 운영 서버 배포를 대신한 것으로 보고하지 않는다.
