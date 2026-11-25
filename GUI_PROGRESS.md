# GUI/System development progress — 2026-11-24

Scope: GUI, read-only derived ROI validation, isolated asynchronous jobs, structured agent GUI control. No model, inference/fusion settings, production DB or services will be changed. Background max16/inference/import jobs must continue untouched.

| Phase | State | Evidence / next action |
|---|---|---|
| 1 redesign | PARTIAL | Original screenshots reviewed; code fixes and current regression checks; new browser acceptance blocked. |
| 2 product meshes | IMPLEMENTED / unit VERIFIED |30-category catalogue, nine families,32 geometry checks, demand rendering, bounds/FOV fit. |
| 3 intro | IMPLEMENTED | Five conceptual cameras, eight stages, CTA/reduced motion. Live visual review blocked. |
| 4 ROI | PARTIAL | Explicit transforms/tests and5-image/96-box audit. No original↔LUT registration; unknown preserved. |
| 5 dashboard | PARTIAL | Data-trust/heatmap/color fixes; missing central queries documented. |
| 6 async jobs | IMPLEMENTED / unit VERIFIED | Separate durable JobStore/API, disabled processor default, opt-in GUI, bounded retries/resume; real inference not run. |
| 7 agent | PARTIAL | Existing tools and links retained, unit read-tool chain and structured local controls; no live LLM action response schema. |
| 8 backfill | VERIFIED read-only inspection | State files advancing; exact user-only report command in final report. No process intervention. |
| 9 PG preparation | VERIFIED documentation | No transition or production schema/data/account changes. |
| 10 integration | VERIFIED automated; browser BLOCKED | Python81pass/4skip; Vitest62pass; lint/TypeScript/build pass; protected hashes unchanged; no HEX violations. Host visual acceptance pending. |

Environment: ps namespace exposes only own invocation; Docker socket denied and localhost:8080 unavailable here. These do not prove host jobs are stopped. No existing process has been signalled or restarted. Tests will use temporary DBs and serial workers.
