# Isolated asynchronous inference jobs

IMPLEMENTED; state/idempotency/concurrency contract tested using lightweight functions. Real model execution intentionally NOT RUN.

Confirmed structural timeout risk: /inference/run awaits run_gui_inference in a threadpool, whose subprocess timeout defaults300s. A disconnected HTTP client may lose a still-running result. Repository logs also contain CORS preflight400s, so every Failed to fetch is not proof of inference timeout. No measured query latency, queue bottleneck or production timeout frequency is invented.

app/jobs.py uses a **dedicated**.sqlite file, not inspection.db/PostgreSQL. QUEUED→RUNNING via transactional claim; RUNNING→COMPLETED/FAILED; QUEUED→CANCELLED. Running work is never killed. A single development worker owns a file lock. Restarted RUNNING work is not automatically rerun; administrative reconciliation is required.

Idempotency-Key maps to a canonical input fingerprint; duplicate input/key returns original Job ID, changed input under the same key409. Aliases are persisted. Capacity12 returns429/Retry-After. All connections close. app/job_api.py returns202+Location+Retry-After, status/result/key-lookup and queued cancellation. Record writes are disabled; no operational schema changes. Processor injection is required; the default factory returns503 for submission and does not launch a worker. Original /inference/run contract remains unchanged.

GUI async mode is opt-in (`VITE_ASYNC_JOBS=true`, `VITE_JOB_API_BASE`), preserving the existing server integration by default. Job endpoint availability is checked against /openapi.json. The original key/ID is persisted locally. Lost POST responses are resolved with the same key; retries do not invent a new job. GET and keyed POST retry only network/timeout,408/429/502/503/504. Exponential backoff with jitter, four attempts, total20s request budget and Retry-After. User navigation aborts polling, not server inference. Monitoring has a10-minute UI wait limit and offers explicit resume. Progress is null; state/stage/time are displayed.

Tests cover persistence, aliases, changed input, concurrent registration/claim, queue capacity, all five states, no running cancellation, one-worker ownership, HTTP response contract, disabled processor, backoff/jitter, permanent failures, unkeyed mutation safety and cancellation. Upload signature/size validation exists; full multipart/network integration remains UNVERIFIED.

Safe disabled development endpoint (no model worker):

```bash
cd /home/geonug/agent
GUI_JOB_DB=/tmp/inspection-gui-development/jobs.sqlite .venv/bin/python -m uvicorn app.job_api:disabled_app --factory --host 127.0.0.1 --port 18081 --workers 1
```

Actual processor wiring and deployment are administrator tasks; not approved or performed here. The read-only GUI gateway intentionally does not serve these mutable job endpoints.
