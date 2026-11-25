# Product template architecture

IMPLEMENTED; geometry/unit contracts VERIFIED. New live browser acceptance BLOCKED.

`inspection-gui/src/three/catalog.ts` separates parameters (family, display size, material, bore, ribs, pins, form) for all30 categories in the real manifest. `parts.ts` generates nine families: connectors, discs, rings, frames, blocks, boards, brush, bead, zipper. Reference contact sheet: reports/gui_validation/category_references.jpg, built from actual C1 images and directly viewed. Example differences: a jack's hollow socket and pins; USB connector shell; bottle-cap ribs; annular nut hole; PCB components; zipper alternating teeth; toothbrush curved handle and bristle tufts. These are approximate category templates, not scanned shapes or dimensional measurements.

Visual `region_id` is stable and separate from statistical ROI validation. Existing toothbrush handle/neck/bristle and toy surface/edge/joint IDs are preserved. Unknown categories use whole/unverified. Mapping status is unverified by default; this alone never authorizes a heatmap assignment.

Scene: PBR roughness/metalness per material; neutral CSS material tokens; no gratuitous bloom. Finite geometry, unique IDs, positive bounds and <45,000 triangles/category verified by32 tests. OrbitControls; center from combined bounds; camera fit uses both vertical and horizontal FOV (narrow viewport supported in code). Explicit parent height fixes partial-height Canvas. Demand rendering, dpr cap1.5, single-frame contact shadows, memoized geometry, disposal on unmount and disposal of merge intermediates. Region selection does not allocate per-frame vectors.

Material caching across separate meshes is not global: R3F owns/disposes each material. CPU parameters/PartDef factories are cached, GPU geometries are not retained across category unmounts. Browser frame time and category-cycle GPU/heap behavior remain UNVERIFIED; no performance improvement percentage is claimed.

Follow-up: detailed geometry/material surfaces now live in modelDetails.ts and shared geometry.ts. Every detail inherits the original category/region; cached definitions and arrays are immutable. Thirty templates include103 detail surfaces, maximum23,892 triangles. SIM is a rectangular tray, not a circular generic frame. Category switching invalidates stale data and namespaces/reset rendering. See DETAILED_3D_HEATMAP_REPORT.md for tests, preview limitations and rendering lifecycle.
