# ROI coordinate mapping investigation

Status **PARTIAL**. Common transforms and audit are implemented/tested; physical LUT registration is **BLOCKED by missing evidence**. No operational findings, ROI configuration or preprocessing was changed.

## Confirmed coordinate path

| Stage | Evidence and coordinates |
|---|---|
| original stored examples | gui_evidence result.json + actual JPEG:1024×1024 |
| RT-DETR input | MV/inference.py preprocess: torchvision Resize([640,640]), direct anisotropic resize, no crop/letterbox/padding |
| RT-DETR output | postprocess normalized cxcywh→xyxy multiplied by orig_sizes; saved boxes are original image coordinates |
| HVQ input | MV/hvq_common.py preprocess Resize([224,224]) and ImageNet normalization; no crop/letterbox/padding |
| HVQ map | model prediction map; source-map size must be read from saved array, not guessed. Existing display overlays resize it to source image for visualization |
| saved GUI findings | app/gui_inference.py records returned original-coordinate xyxy; no LUT registration metadata persisted |
| legacy LUT | config/parts_roi.json roi-lut-v1,640×480, toothbrush/toy regions |
| newer parts-roi-v1 |1024×1024 with unknown regions; no category registration proof |
| mesh regions | stable display IDs; not a geometric projection or physical ROI registration |

Thus1024×1024 is an original image size, **not both model input sizes**. Knowing direct model resize does not prove how a manually authored640×480 LUT relates to that original. We did not stretch the LUT just to reduce unknown.

## Implemented layer

app/coordinates.py supports explicit affine resize/crop/pad, inverse/composition, normalized coordinates, bbox/polygon conversion, range checks and map warping with pixel-center handling. Transform and mapping versions plus provenance are required. Map padding removal uses the inverse transform. Source/target map dimensions must match. LUT target dimensions must match the referenced mapping. Missing registration remains unknown/unverified even when image sizes happen to match.

## Actual stored-result audit

scripts/audit_roi_coordinates.py reads saved result.json files, deduplicates images by content hash/camera and writes separate derived JSON/HTML only. Five unique toothbrush images,96 model detections. Coverage is one category; other29 categories were not falsely claimed validated.

| Camera | boxes | old unknown | derived unknown/unverified |
|---|---:|---:|---:|
| C1 |25|25|25|
| C2 |35|32|35|
| C3 |10|9|10|
| C4 |15|15|15|
| C5 |11|6|11|
| Total |96|87 (90.625%)|96 (100%)|

The nine old non-unknown assignments lack registration proof. Treating them as verified would be misleading. This is conservative data handling, not a model accuracy improvement. No operational values were overwritten.

Open reports/gui_validation/roi_overlay.html on the host: actual original images with stored RT boxes are shown alongside native640×480 LUT reference planes. A combined original+ROI overlay is deliberately not represented as valid without an original↔LUT registration. Latest browser visual acceptance of this HTML remains pending. The category contact sheet was visually reviewed; that is separate evidence.

Tests cover inverse resize, explicit crop/padding, polygon, normalized composition, map inverse/padding removal, invalid boxes, external ROI locations, boundary centers, missing metadata and LUT-size mismatch. Remaining: obtain camera/category-specific registration, physically verify region IDs, then run representative category/camera overlays and compare mapping rates. Unknowns outside ROIs must remain unknown.


## Follow-up: unknown0/1 and handle tooltip

Confirmed source code separates legacy confirmed reviews from fusion_analysis product scores. Entire24,000product completion does not populate physical part registration. UI now distinguishes unknown/unmapped grouped evidence, no reviewed samples, API error and mapping unverified; unknown is no longer colored as a normal0% product region. Physical registration remains missing and no operational data/ROI config was changed. See COHORT_AND_PART_MAPPING_REPORT.md.


## Native exact-image registration now implemented

Latest user requested implementation and removal of the unobserved handle. A separate config/part_heatmap_regions.json now registers native1024² polygons for the actually inspected toothbrush head in five exact image hashes. No legacy640×480 LUT stretch was used. Stored RT boxes and224² HVQ maps are aggregated through common transforms and pixel-center masks. The generated original-image overlay reports/part_heatmap/native-roi-review.jpg was directly reviewed. RT0.4 yields6mapped boxes but only1positive observed product; uploaded copies are deduplicated. app/part_api.py and the frontend now render this source as model-suspicion evidence, with original ROI/box views. This does not establish population-wide registration, confirmed defects, or coverage for other categories/neck. Live GUI rendering is still unverified. See NEXT_AGENT_HANDOFF.md.
