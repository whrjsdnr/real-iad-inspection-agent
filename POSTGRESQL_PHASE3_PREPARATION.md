# PostgreSQL sharing preparation — no transition performed

Current architecture inspected: app.db role-specific SQLAlchemy engines; DATABASE_URL fallback SQLite; read/review/workflow/batch optional URLs; dbconn shares engine; existing compose/Alembic/transfer/export scripts. GUI only requests central FastAPI APIs, not DB credentials. Main app lifespan calls migrate/start_worker; therefore it was NOT started against production during this work.

A separate app.readonly_api development gateway uses only DATABASE_URL_READ, explicitly read-only transactions, no migrations/workers/inference/review writes. It shares only registered read handlers. /api Vite proxy fixes browser-origin coupling without modifying production CORS or DB configuration.

SQLite dependencies include local fallback, metrics/import helpers, separate dev JobStore, optional score/backfill stores outside this project. Dev JobStore is intentionally separate and not part of any PG migration. Existing PG fusion_analysis schemas are outside the four legacy ORM inspection tables; matching column/table names does not prove identical semantics. Model run IDs/score sets and reviews must not be flattened or mixed during future transition.

Before an authorized future transition: verify real source schema, row counts, PKs, model/mapping versions, timestamp policy, review optimistic locking and read-only credentials; create isolated migration target; perform transfer+count validation; run API contract and concurrent-review tests; backup/restore rehearsal. Switch URL only after approval. Rollback points the isolated application back to the previous validated URL after stopping only its own writes. Do not overwrite newer operational reviews with an old snapshot.

No PostgreSQL schema/data/account/permission changes, compose starts, migration executions or production URL switches were performed. Docker socket is inaccessible in the sandbox; host status was not inferred from that denial.
