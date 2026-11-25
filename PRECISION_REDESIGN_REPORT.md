# Team V6 Precision intro and dashboard integration

2026-11-24. IMPLEMENTED; automated checks VERIFIED; latest browser visual acceptance remains BLOCKED by the previously documented host/sandbox socket boundary.

## Requested result

Use inspect_ai_v6_precision.html as the intro, and carry its visual language into the real dashboard. The original468,408-byte teammate file is unchanged (SHA256 recorded in reports/gui_validation/precision_source.json). Its procedural flange, five cameras, per-view capture previews and dual-model illustrations are retained in an isolated sandboxed iframe.

The prototype dashboard is never exposed as real inspection data. Its skip button sends one validated parent message, and actual navigation opens the existing #/dashboard. The parent checks exact iframe source and an exact command/destination shape. Iframe has scripts only, no same-origin permission, and CSP blocks network, forms and nested frames. All simulation labels remain visible. No operational API, inference or database call is made by the intro.

The normal intro stops at its final frame instead of unexpectedly forcing navigation. Immediate real CTA buttons remain outside the iframe. Pause/replay/seek controls remain. Reduced-motion and CPU fallback modes start static at the five-view stage; step buttons remain usable. Hidden tabs and paused scenes stop their animation loop, WebGL rendering is capped at24fps, and disposal cancels RAF/releases buffers/context. Actual FPS and memory are not measured.

The previous eight-stage R3F intro remains available via “기존 개념 인트로”. The default V6 uses its original five visible timeline phases. The large source is lazy-loaded as a separate intro chunk (473.44KB / gzip55.70KB), not added to every dashboard route's eager content.

## Real dashboard design

- Shared scoped Precision theme: navy background, cyan highlights, rounded panels, subtle edge lighting and restrained shadows.
- INSPECT AI navigation and a new dashboard hero with existing AI-agent/five-view links.
- Clearly separated performance/baseline summary, inspection condition rail, central3D visualization and right evidence panel.
- Wider readable labels, consistent controls and mobile wrapping; fixed overlapping sticky headers.
- Original filters, part selection, evidence links, review flow, API/fixture separation and heatmap data gates retained.
- Missing FP/FN no longer displays a manufactured total0.
- Approximate category meshes remain the actual dashboard models. The intro flange is a simulation model, not a replacement for inspection category data.

All116 source palette colors were centralized in tokens.css. CSS and Canvas color strings in the integrated prototype resolve through tokens. Shader numeric lighting/material colors are preserved as part of the teammate's isolated renderer. No new package was installed.

## Validation

- Vitest: **66 passed /11 files** (includes prototype isolation/routing/motion/lifecycle/message checks).
- ESLint passed.
- TypeScript + production build passed; existing large-chunk warning remains.
- Integrated iframe inline script compiled with Node vm.Script for syntax only, not executed.
- Original teammate HTML SHA256 unchanged.
- Protected inference/config hashes unchanged; no hardcoded HEX outside the token file.

Logs: reports/gui_validation/precision-{vitest,eslint,build,integrity}.log. Adapted standalone audit artifact: reports/gui_validation/precision-integrated.html. That file is not a newly captured screenshot and is not an operational dashboard.

## Changed files

IntroPage.tsx; new intro/PrecisionIntro.tsx, precisionDocument.ts and tests; App.tsx; DashboardPage.tsx; CenterPanel/FilterPanel/LeftPanel/RightPanel/TopBar; index.css, styles/tokens.css, utils/tokens.ts. Host screenshot harness now selects the iframe's camera/model-evidence stages.

## Viewing and acceptance

Refresh the existing development GUI to see the new default intro, then use “대시보드 시작하기”. For an isolated read-only host preview: bash scripts/start_gui_readonly.sh, then http://127.0.0.1:15173/. The current sandbox cannot confirm actual host rendering. Run nice -n15 node scripts/capture_gui_validation.mjs on host and visually review intro/camera/model-evidence/dashboard/mobile screenshots. No operational API restart or model/background process action was performed.
