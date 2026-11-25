# 재현 방법

## 환경
- Python 3.12 + uv(~/agent/.venv), Node 20+(inspection-gui), PostgreSQL 16(:5432/inspection), Ollama(선택).
- 자격증명은 루트 `.env`(Git 제외). 예시는 `.env.example`.

## 백엔드 실행
```bash
cd ~/agent && set -a && source .env && set +a
.venv/bin/python -m pytest -q                      # 133 passed / 4 skipped
.venv/bin/python -m uvicorn app.api:app --host 0.0.0.0 --port 8000
.venv/bin/python -m uvicorn app.readonly_api:app --host 127.0.0.1 --port 18080   # DATABASE_URL_READ 필요
```

## GUI 실행
```bash
cd ~/agent/inspection-gui
npm ci && npx vitest run                           # 135 passed / 23 파일
npm run build && npm run dev -- --port 15173       # Vite + /api 프록시(18080)
```

## 퓨전 평가 재생성(추론 없음)
```bash
.venv/bin/python scripts/report_minmax_fusion.py   # 저장 점수 SQLite → reports/final_performance_minmax/
.venv/bin/python scripts/check_final_sync.py --base-url http://127.0.0.1:18080
```

## 공유 패키지 재생성
```bash
PYTHONPATH=/home/geonug/agent .venv/bin/python scripts/build_team_integration_kit.py
unzip -t team_integration_kit.zip && sha256sum team_integration_kit.zip
```

## 주의
- 모델 추론·학습은 ~/MV 자산을 그대로 사용하고, 보호 대상(`inference.py`·`inference_hvq.py`·`report_fusion_performance.py`)은 수정하지 않는다.
- 운영 DB 스키마·기존 판정은 변경 금지. 실데이터 기록 전 백업(`scripts/backup.sh`) 확인.
- 추론·백필·동기화 같은 장기 배치는 nohup + 전용 로그로 기동하고 PID를 기록한다.
