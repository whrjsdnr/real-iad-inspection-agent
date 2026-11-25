# Five-camera intro

IMPLEMENTED, build verified; latest live rendering BLOCKED.

IntroScene.tsx reuses the toothbrush template on a stage, five industrial camera meshes, C1–C5 labels and line-of-sight geometry. Layout is explicitly conceptual; actual camera orientation is not inferred from dataset camera IDs. Eight stages: product placement, camera layout, capture, RT boxes, HVQ anomaly illustration, product fusion, region emphasis, AI explanation. Orange box and translucent anomaly patch are explicitly demonstration graphics, not inspection data. No fake numeric model score is displayed.

Step buttons support manual navigation; timed progression uses one cleaned-up timeout, pauses, stops at the final stage and obeys prefers-reduced-motion. Both CTA buttons are accessible immediately, independent of animation completion. Reduced motion shows a static final conceptual scene. React routing unmounts inactive scenes; Canvas uses demand rendering. Existing CSS tokens are retained, material tokens added only in tokens.css.

Old intro.png was directly inspected and its CTA was visible. New screenshots are not available under this sandbox; do not reuse the old PNG as evidence of this implementation. Host capture procedure: FINAL_GUI_VALIDATION_REPORT.md.

Follow-up: User supplied inspect_ai_v6_precision.html and requested its design. The default intro now preserves its original procedural flange/five-view design through a network-isolated sandboxed iframe. The earlier8-stage scene remains accessible as an alternative. See PRECISION_REDESIGN_REPORT.md for timing, lifecycle, parent navigation and validation details.
