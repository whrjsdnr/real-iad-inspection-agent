# API connection fix

Observed: frontend used absolute http://localhost:8080. config/web.json only permits localhost/127.0.0.1:5173; logs/gui_api.log records OPTIONS /tools/query_error_stats returning400, and its last lines record API process225738 shutting down. These prove a past CORS rejection and shutdown, not the current host process state (sandbox has a separate process/network namespace).

Implemented: default API_BASE=/api and Vite dev/preview proxy to GUI_API_TARGET (default127.0.0.1:8080). Browser no longer requires cross-origin preflight. Operational CORS config was not changed. apiProxy.test.ts checks rewriting and target validation.

If8080 API is down, the proxy cannot fix that. Start a separate read-only gateway and GUI from host Ubuntu:

```bash
cd /home/geonug/agent
bash scripts/start_gui_readonly.sh
```

Open http://127.0.0.1:15173/ and reload. The script requires DATABASE_URL_READ in the existing.env, binds only unused18080/15173, never kills an existing process, and never migrates the DB or starts inference/backfill/import/review workers. PostgreSQL transactions use SET TRANSACTION READ ONLY. SQLite uses query_only. Exit stops only the new gateway child. Log: /tmp/inspection-gui-readonly-api.log.

For an already running8080 API, simply restart only your development Vite with its default `/api` path (`npm --prefix inspection-gui run dev`). Do not restart the operational API. Remove a shell-supplied VITE_API_BASE=http://localhost:8080 override to use the proxy. Static production hosting requires a separately approved reverse proxy; none was deployed here.

Runtime repair on host is UNVERIFIED: sandbox cannot access host sockets. User must run the command above. Read-only gateway deliberately omits chat, inference and review write endpoints; the original full API remains unchanged.
