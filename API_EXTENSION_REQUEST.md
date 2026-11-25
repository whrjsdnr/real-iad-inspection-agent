# Central API extension request (not deployed)

Current source contract: app/api.py GET /health,/items,/status/overview,/performance/final,/metrics/snapshots,/inference/sample_products; POST /tools/{name},/chat,/inference/run. Central live OpenAPI is unreachable in the sandbox. Source inspection is VERIFIED; deployed version is UNVERIFIED. New GUI job client checks /openapi.json for required job paths before registration.

| Requirement | Current support | Gap |
|---|---|---|
| product/category and camera evidence | items, sample_products, get_case_evidence(product_id) | general paginated products/count-distinct endpoint absent |
| confirmed part rates | query_error_stats, compute_inspection_metrics | product×part dedup, coordinate-proven ROI and latest-review coverage need validation |
| high anomaly products/model disagreement/unmapped products | raw findings/evidence partially available | registered bounded read tools absent; do not invent their names in LLM calls |
| model comparison page | final performance summary; inference result has two model scores | no standalone comparison route; no fabricated navigation target |
| GUI commands from LLM | local validated dispatcher/context controls implemented | /chat has no structured action/trace response schema; central extension needed |
| async inference | original synchronous /inference/run retained | separate app/job_api.py factory implemented; central deployment requires administrator review |
| coordinate registration | legacy LUT and raw image sizes | versioned original↔LUT registration, orientation and physical region correspondence missing |

Proposed future server work must expose bounded read-only queries, distinct product counts separate from box counts, numerator/denominator, sample size, source/model/transform versions, and explicit unavailable reasons. No production schema changes were made. No unknown endpoint is silently called as a substitute for a missing feature.


## Final performance synchronization inspection

get_final_performance HTTP input registration was missing and is now implemented locally. Existing background_code_v1 snapshot already registers compute_fusion_metrics/get_fusion_case_evidence against fusion_analysis, but the current GUI repository does not; live server OpenAPI/tools could not be reached. Treat these as a source/version parity gap, not proof the central service lacks them. Do not call them unless the connected service actually registers them. See FINAL_PERFORMANCE_SYNC_REPORT.md.
