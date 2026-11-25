# Dashboard data trust contract

PARTIAL. Existing APIs/UI retained; no new operational aggregates fabricated.

API mode: failed queries return an explicit error and empty cases/rows or null rates with backend_unavailable reason. No automatic fixture substitution. Genuine empty responses carry no connection error and are not normal/defect classifications. Explicit VITE_USE_FIXTURE=true is separate fixture mode; LLM direct-tool fallback is labelled separately from fixture inspection data. Tests cover network failure, valid empty data and explicit fixture selection.

SourceBadge/error banner distinguishes API failure. Failed responses are not cached as successful heatmap statistics. CSS/material tokens distinguish unknown data from a measured rate of zero. No new statistical mapping is attached to new visual regions without ROI registration. A production map cannot be considered trustworthy solely because a legacy part_id string matches a template.

Existing category/date/metric/model filters still invoke existing tool APIs. Production default model filter is all instead of mock-anomaly-v1. Case evidence by product/camera keeps original model/version/review evidence. A bug clearing focusCase before the async lookup completed was fixed so cleanup no longer cancels all deep-link results.

Existing reported98.84% is shown as a historical user-provided number with unknown metric name/denominator, separate from live performance summaries. No claim of current operational accuracy was added. Existing report readiness/data timestamps remain API driven.

Remaining central API gaps are in API_EXTENSION_REQUEST.md: paginated product explorer, score-range and disagreement queries, distinct product vs box counts, per-region aggregate reliability and full FP/FN coverage. No replacement fake data is used for missing APIs. Live backend/browser integration is UNVERIFIED from this sandbox.


## Whole-cohort reference and part provenance follow-up

Final performance metrics now have evaluation_scope (test/all_inferred_products_reference), evaluation_products, test_products (always original Test count), test_f1_micro/test_recall/test_reference, contains_calibration_products, training_overlap, csv_consistency_verified. Source-bound reports/cohort_performance/latest.json provides all-product aggregation when source path/SHA/model/count match; otherwise Test remains selected. All-product CSV/manifest consistency is separate from independent SQL verification; verified stays false for this derived report. No stored verdict is modified.

query_error_stats source_scope is confirmed_reviews (or inspection_attempts for capture/process failures), mapping_verified=false. unknown/group denominator is not the inferred cohort count. The GUI keeps unknown evidence neutral and does not attach it to a handle region. Manual statistics refresh bypasses cache; it is not whole-application automatic synchronization.
