# Agent and GUI integration

PARTIAL. Existing Qwen/chat/tool registry and evidence links retained. No live LLM request was made during background inference/backfill.

Inspected registry: query_error_stats, get_case_evidence, get_training_status, request_review, get_final_performance. Arbitrary SQL/JS/eval tools are rejected. A regression test exercises real isolated seeded-data stats→stat_key→evidence queries through agent.run_tool; it is a unit smoke check, not a successful live Qwen loop.

Current category/product/region is embedded as data context in the existing /chat.question string. No unsupported request field or invented tool endpoint is sent. Chat HTTP has a bounded60s wait and visible failure state. Server unavailable, direct tool responses (LLM disconnected) and explicit fixture data are separately labelled. Product-ID evidence links still navigate to existing dashboard deep links.

New local structured GUI registry validates exact keys/enums for category/product/camera/region/camera pose/heatmap metric/navigation. Unknown categories/regions, arbitrary code, extra fields and external destinations are rejected. GUI context controls provide category selection, region emphasis and dashboard navigation. CenterPanel exposes explicit camera poses. This local control path is tested; it does not claim the deployed LLM emits GUI commands.

The central /chat response has answer/mode only, with no action/trace schema. Automated LLM→GUI dispatch, new data queries and comparison-screen navigation remain missing and are recorded in API_EXTENSION_REQUEST.md. Do not silently treat answer text as executable commands. Live GUI/chat match and real Qwen loop remain UNVERIFIED.
