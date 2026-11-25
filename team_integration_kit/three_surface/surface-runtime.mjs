// <define:import.meta.env>
var define_import_meta_env_default = {};

// inspection-gui/src/three/surfaceSdk.ts
import * as T3 from "three";

// inspection-gui/src/three/surfaceProjection.ts
import * as T from "three";

// inspection-gui/src/three/spatialGrid.ts
import { DataTexture, RGBAFormat, UnsignedByteType, NearestFilter, SRGBColorSpace } from "three";

// inspection-gui/src/config.ts
var API_BASE = define_import_meta_env_default.VITE_API_BASE ?? "/api";
var USE_FIXTURE = define_import_meta_env_default.VITE_USE_FIXTURE === "true";
var MIN_DENOMINATOR = 10;

// source-text:/home/geonug/agent/inspection-gui/src/styles/tokens.css
var tokens_default = "/**\n * \uB514\uC790\uC778 \uD1A0\uD070 \u2014 mission control (\uB2E4\uD06C \uAD00\uC81C\uC2E4).\n * \uC804 \uD654\uBA74\uC740 \uC774 \uBCC0\uC218(\uB610\uB294 tailwind \uD314\uB808\uD2B8\uAC00 \uC774 \uBCC0\uC218\uB97C \uCC38\uC870)\uB9CC \uC0AC\uC6A9\uD55C\uB2E4.\n * RGB \uD2B8\uB9AC\uD50C\uB9BF\uC740 tailwind\uC758 <alpha-value> \uCE58\uD658\uC6A9\uC774\uB2E4.\n */\n\n:root {\n  /* \uC0C9\uC0C1 */\n  --bg: #0a0b0d;\n  --panel: #121316;\n  --panel-raised: #17191d;\n  --line: #262a31;\n  --signal: #ff9e40;\n  --ok: #5fa8c7;\n  --warn: #d9a24a;\n  --fail: #d85c46;\n  --text: #fbfbfb;\n  --muted: #b8bcc4;\n  --faint: #9299a4;\n\n  /* \uD30C\uC0DD \uBA38\uD2F0\uB9AC\uC5BC \u2014 \uAE00\uB798\uC2A4(\uB5A0 \uC788\uB294 \uC624\uBC84\uB808\uC774 \uC804\uC6A9), --bg 72% */\n  --glass-bg: rgba(10, 11, 13, 0.72);\n  --hairline: rgba(255, 255, 255, 0.06);\n\n  /* --signal \uAE00\uB85C\uC6B0 \uB808\uC774\uC5B4 (0.1~0.36) */\n  --glow-signal-10: rgba(255, 158, 64, 0.1);\n  --glow-signal-18: rgba(255, 158, 64, 0.18);\n  --glow-signal-28: rgba(255, 158, 64, 0.28);\n  --glow-signal-36: rgba(255, 158, 64, 0.36);\n\n  /* \uD788\uD2B8\uB9F5 \uC575\uCEE4 \u2014 heat.ts\uAC00 \uC774 \uAC12\uC5D0\uC11C \uC0AC\uB2E4\uB9AC\uB97C \uD30C\uC0DD\uD55C\uB2E4. */\n  --heat-ok: #16c9ff;\n  --heat-warn: #ffe066;\n  --heat-fail: #ff3848;\n\n  --scroll-thumb: rgba(146, 153, 164, 0.45);\n  --material-plastic: #c5ccd3;\n  --material-metal: #a3b4c2;\n  --material-rubber: #404951;\n  --material-board: #477a77;\n  --material-wood: #c2a77b;\n  --material-ceramic: #dfd5d0;\n  --material-contact: #bba67c;\n\n  /* \uD0C0\uC774\uD3EC */\n  --font-ui:\n    'Inter', 'Pretendard', system-ui, -apple-system, 'Segoe UI', 'Malgun Gothic',\n    sans-serif;\n  --font-mono: 'JetBrains Mono', ui-monospace, 'SFMono-Regular', 'Malgun Gothic',\n    monospace;\n\n  /* \uADF8\uB9AC\uB4DC/\uD615\uD0DC */\n  --radius: 6px;\n  --radius-lg: 8px;\n\n  /* \uBAA8\uC158 */\n  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);\n  --dur: 0.56s;\n  --stagger: 70ms;\n  --hover-dur: 0.15s;\n  --pulse-dur: 1.4s;\n  --cta-dur: 3.4s;\n  --grid-pan-dur: 38s;\n\n  /* RGB \uD2B8\uB9AC\uD50C\uB9BF (tailwind <alpha-value> \uC5F0\uB3D9) */\n  --c-bg: 10 11 13;\n  --c-panel: 18 19 22;\n  --c-panel-raised: 23 25 29;\n  --c-line: 38 42 49;\n  --c-signal: 255 158 64;\n  --c-ok: 95 168 199;\n  --c-warn: 217 162 74;\n  --c-fail: 216 92 70;\n  --c-text: 251 251 251;\n  --c-muted: 184 188 196;\n  --c-faint: 146 153 164;\n  --c-white: 255 255 255;\n\n  /* --signal \uC704\uC758 \uC804\uACBD\uC0C9 (CTA \uD14D\uC2A4\uD2B8) */\n  --on-signal: #14100a;\n}\n\n/* Team precision intro palette \u2014 source inspect_ai_v6_precision.html. */\n:root {\n  --precision-color-000: #000;\n  --precision-color-001: #0002;\n  --precision-color-002: #0004;\n  --precision-color-003: #0005;\n  --precision-color-004: #0006;\n  --precision-color-005: #0008;\n  --precision-color-006: #03080dbd;\n  --precision-color-007: #03080dc9;\n  --precision-color-008: #040a12de;\n  --precision-color-009: #050a1240;\n  --precision-color-010: #050a12e8;\n  --precision-color-011: #060b12;\n  --precision-color-012: #071019;\n  --precision-color-013: #080f17;\n  --precision-color-014: #08121c;\n  --precision-color-015: #08121de8;\n  --precision-color-016: #081522eb;\n  --precision-color-017: #09121a;\n  --precision-color-018: #091520;\n  --precision-color-019: #0a131c;\n  --precision-color-020: #0a1520;\n  --precision-color-021: #0b1622;\n  --precision-color-022: #0b1723;\n  --precision-color-023: #0b1c27db;\n  --precision-color-024: #0b1c28d9;\n  --precision-color-025: #0c1722;\n  --precision-color-026: #0c1823;\n  --precision-color-027: #0c202bdc;\n  --precision-color-028: #0e1b27;\n  --precision-color-029: #10202e;\n  --precision-color-030: #103646;\n  --precision-color-031: #122331;\n  --precision-color-032: #1232c7;\n  --precision-color-033: #123849;\n  --precision-color-034: #132431;\n  --precision-color-035: #142331;\n  --precision-color-036: #153745;\n  --precision-color-037: #16a3f4;\n  --precision-color-038: #173b4b;\n  --precision-color-039: #1a242d;\n  --precision-color-040: #1b3545;\n  --precision-color-041: #1ce9ab;\n  --precision-color-042: #201c16;\n  --precision-color-043: #20daf326;\n  --precision-color-044: #20daf366;\n  --precision-color-045: #223442;\n  --precision-color-046: #243d4b;\n  --precision-color-047: #253b4b;\n  --precision-color-048: #263c4c;\n  --precision-color-049: #263d4d;\n  --precision-color-050: #283d4e;\n  --precision-color-051: #2a4151;\n  --precision-color-052: #2b4555;\n  --precision-color-053: #2b4557;\n  --precision-color-054: #311a22df;\n  --precision-color-055: #345064;\n  --precision-color-056: #36576a;\n  --precision-color-057: #385365;\n  --precision-color-058: #386477;\n  --precision-color-059: #3b687b;\n  --precision-color-060: #3d7286;\n  --precision-color-061: #426071;\n  --precision-color-062: #45dbe7;\n  --precision-color-063: #48e5f8;\n  --precision-color-064: #49e6fa;\n  --precision-color-065: #4fe6ff;\n  --precision-color-066: #50e6f5;\n  --precision-color-067: #5292a9;\n  --precision-color-068: #554a35;\n  --precision-color-069: #55e4f4;\n  --precision-color-070: #5ae8f4;\n  --precision-color-071: #60f3ff;\n  --precision-color-072: #79dcf0;\n  --precision-color-073: #82e8f1;\n  --precision-color-074: #849aac;\n  --precision-color-075: #8598a4;\n  --precision-color-076: #8ca6b9;\n  --precision-color-077: #8eacbf;\n  --precision-color-078: #8fa5b6;\n  --precision-color-079: #91a7b9;\n  --precision-color-080: #93b2c4;\n  --precision-color-081: #982a43;\n  --precision-color-082: #9ab2c4;\n  --precision-color-083: #9bf6ff;\n  --precision-color-084: #9db5c5;\n  --precision-color-085: #9eb1c1;\n  --precision-color-086: #9eb7c7;\n  --precision-color-087: #a14c5d;\n  --precision-color-088: #a1b8c9;\n  --precision-color-089: #a4faff;\n  --precision-color-090: #a6bfce;\n  --precision-color-091: #a7f4ff;\n  --precision-color-092: #a9e6ff13;\n  --precision-color-093: #afd5e5;\n  --precision-color-094: #b7c9d5;\n  --precision-color-095: #b7faff;\n  --precision-color-096: #c58b58;\n  --precision-color-097: #d1beab;\n  --precision-color-098: #d5e8f3;\n  --precision-color-099: #dfaa68;\n  --precision-color-100: #e0f4f8;\n  --precision-color-101: #e7eff6;\n  --precision-color-102: #e8c38f;\n  --precision-color-103: #e8f5fa;\n  --precision-color-104: #ed4148;\n  --precision-color-105: #f2be7f;\n  --precision-color-106: #f6516d44;\n  --precision-color-107: #fce044;\n  --precision-color-108: #ff596766;\n  --precision-color-109: #ff6a7a;\n  --precision-color-110: #ff7489;\n  --precision-color-111: #ff9ca8;\n  --precision-color-112: #ff9eab;\n  --precision-color-113: #ffb3ab;\n  --precision-color-114: #ffc184;\n  --precision-color-115: #fff;\n}\n\n/* Scoped Precision dashboard theme \u2014 palette shared with the team intro. */\n.precision-shell {\n  --bg: var(--precision-color-011);\n  --c-bg: 6 11 18;\n  --panel: var(--precision-color-025);\n  --c-panel: 12 23 34;\n  --panel-raised: var(--precision-color-029);\n  --c-panel-raised: 16 32 46;\n  --line: var(--precision-color-048);\n  --c-line: 38 60 76;\n  --signal: var(--precision-color-064);\n  --c-signal: 73 230 250;\n  --text: var(--precision-color-101);\n  --c-text: 231 239 246;\n  --muted: var(--precision-color-085);\n  --c-muted: 158 177 193;\n  --faint: var(--precision-color-078);\n  --c-faint: 143 165 182;\n  --on-signal: var(--precision-color-011);\n  --radius: 10px;\n  --radius-lg: 14px;\n  --precision-shadow: 0 14px 42px rgba(0, 0, 0, 0.24);\n  --precision-rule: color-mix(in srgb, var(--signal) 20%, var(--line));\n}\n\n/* Detailed inspection viewport materials. */\n:root { --material-stage: #253744; --material-muted: #747f8b; }\n";

// inspection-gui/src/utils/tokens.ts
function cssVar(name, fallback = "") {
  if (typeof document !== "undefined" && typeof getComputedStyle !== "undefined") {
    const value = getComputedStyle(document.querySelector("[data-inspection-theme]") ?? document.documentElement).getPropertyValue(name).trim();
    if (value) return value;
  }
  const line = tokens_default.split("\n").find((row) => row.trim().startsWith(`${name}:`));
  return line?.slice(line.indexOf(":") + 1).split(";")[0].trim() ?? fallback;
}
function tokenRgb(name) {
  const color = cssVar(name).replace("#", "");
  if (!/^[\da-f]{6}$/i.test(color)) throw new Error(`Expected RGB hex token: ${name}`);
  return [parseInt(color.slice(0, 2), 16), parseInt(color.slice(2, 4), 16), parseInt(color.slice(4, 6), 16)];
}

// inspection-gui/src/utils/heat.ts
var NULL_COLOR = cssVar("--faint");
var HEAT_OK = tokenRgb("--heat-ok");
var HEAT_WARN = tokenRgb("--heat-warn");
var HEAT_FAIL = tokenRgb("--heat-fail");
var BG = tokenRgb("--bg");
function mix(a, b, t) {
  const k = Math.min(1, Math.max(0, t));
  return [
    a[0] + (b[0] - a[0]) * k,
    a[1] + (b[1] - a[1]) * k,
    a[2] + (b[2] - a[2]) * k
  ];
}
var STOPS = [
  [0, mix(HEAT_OK, BG, 0.25)],
  [0.42, HEAT_OK],
  [0.72, HEAT_WARN],
  [1, HEAT_FAIL]
];
function toHex([r, g, b]) {
  const h = (v) => Math.round(v).toString(16).padStart(2, "0").toUpperCase();
  return `#${h(r)}${h(g)}${h(b)}`;
}
var HEAT_GRADIENT_CSS = `linear-gradient(90deg, ${STOPS.map(
  ([t, c]) => `${toHex(c)} ${t * 100}%`
).join(", ")})`;

// inspection-gui/src/three/surfaceProjection.ts
function modelUV(point, bounds, projection) {
  const [a, b] = projection.axes;
  let u = (point[a] - bounds.min[a]) / Math.max(1e-9, bounds.max[a] - bounds.min[a]);
  let v = 1 - (point[b] - bounds.min[b]) / Math.max(1e-9, bounds.max[b] - bounds.min[b]);
  for (let turn = 0; turn < (projection.quarter_turns % 4 + 4) % 4; turn++) [u, v] = [v, 1 - u];
  return [T.MathUtils.clamp(u, 0, 1), T.MathUtils.clamp(v, 0, 1)];
}
function sourceToModel(u, v, bounds, projection) {
  for (let turn = 0; turn < (projection.quarter_turns % 4 + 4) % 4; turn++) [u, v] = [1 - v, u];
  const [a, b] = projection.axes, normal = ["x", "y", "z"].find((axis) => axis !== a && axis !== b);
  const point = new T.Vector3();
  point[a] = T.MathUtils.lerp(bounds.min[a], bounds.max[a], u);
  point[b] = T.MathUtils.lerp(bounds.min[b], bounds.max[b], 1 - v);
  point[normal] = projection.normal_sign > 0 ? bounds.max[normal] : bounds.min[normal];
  return point;
}
function projectedGeometry(source, bounds, projection, minCos) {
  const temporary = source.index ? source.toNonIndexed() : source.clone(), position = temporary.getAttribute("position"), normal = temporary.getAttribute("normal");
  const p = [], n = [], uv = [], a = new T.Vector3(), b = new T.Vector3(), c = new T.Vector3();
  const axis = ["x", "y", "z"].find((axis2) => !projection.axes.includes(axis2));
  for (let i = 0; i < position.count; i += 3) {
    a.fromBufferAttribute(position, i);
    b.fromBufferAttribute(position, i + 1);
    c.fromBufferAttribute(position, i + 2);
    const facing = b.clone().sub(a).cross(c.clone().sub(a)).normalize()[axis] * projection.normal_sign;
    if (facing < minCos) continue;
    for (let j = 0; j < 3; j++) {
      const point = new T.Vector3().fromBufferAttribute(position, i + j);
      p.push(point.x, point.y, point.z);
      n.push(normal.getX(i + j), normal.getY(i + j), normal.getZ(i + j));
      uv.push(...modelUV(point, bounds, projection));
    }
  }
  temporary.dispose();
  const result = new T.BufferGeometry();
  result.setAttribute("position", new T.Float32BufferAttribute(p, 3));
  result.setAttribute("normal", new T.Float32BufferAttribute(n, 3));
  result.setAttribute("uv", new T.Float32BufferAttribute(uv, 2));
  result.computeBoundingBox();
  result.computeBoundingSphere();
  return result;
}
function surfaceFieldTextures(region) {
  const values = region.values.filter((value, index) => value !== null && region.valid_observation_counts[index] > 0 && !!region.coverage_mask[index]);
  const min = values.length ? Math.min(...values) : 0, max = values.length ? Math.max(...values) : 0;
  if (!(max > 0)) return null;
  const field = new Uint8Array(region.grid_width * region.grid_height * 4), coverage = new Uint8Array(field.length);
  region.values.forEach((value, index) => {
    if (value === null || region.valid_observation_counts[index] <= 0 || !region.coverage_mask[index]) return;
    const normalized = max > min ? (value - min) / (max - min) : 1;
    field[index * 4] = Math.round(normalized * 255);
    field[index * 4 + 3] = 255;
    coverage.set([255, 255, 255, 255], index * 4);
  });
  const signal = new T.DataTexture(field, region.grid_width, region.grid_height, T.RGBAFormat, T.UnsignedByteType);
  signal.minFilter = signal.magFilter = T.LinearFilter;
  signal.flipY = false;
  signal.needsUpdate = true;
  const mask = new T.DataTexture(coverage, region.grid_width, region.grid_height, T.RGBAFormat, T.UnsignedByteType);
  mask.minFilter = mask.magFilter = T.NearestFilter;
  mask.flipY = false;
  mask.needsUpdate = true;
  return { signal, mask, min, max, dispose: () => {
    signal.dispose();
    mask.dispose();
  } };
}
function mappedHotspots(geometries, bounds, frame, region) {
  const material = new T.MeshBasicMaterial({ side: T.DoubleSide }), meshes = geometries.map((geometry) => new T.Mesh(geometry, material));
  meshes.forEach((mesh) => mesh.updateMatrixWorld(true));
  const axis = ["x", "y", "z"].find((axis2) => !frame.projection.axes.includes(axis2));
  const direction = new T.Vector3();
  direction[axis] = -frame.projection.normal_sign;
  const distance = Math.max(1, bounds.getSize(new T.Vector3()).length()), ray = new T.Raycaster(), hits = [];
  const ranked = region.values.map((value, index) => ({ value, index })).filter((cell) => cell.value !== null && cell.value > 0 && region.valid_observation_counts[cell.index] > 0 && !!region.coverage_mask[cell.index]).sort((a, b) => b.value - a.value);
  for (const cell of ranked.slice(0, frame.hotspot_candidate_limit)) {
    const column = cell.index % region.grid_width, row = Math.floor(cell.index / region.grid_width);
    const origin = sourceToModel((column + 0.5) / region.grid_width, (row + 0.5) / region.grid_height, bounds, frame.projection);
    origin[axis] += frame.projection.normal_sign * distance;
    ray.set(origin, direction);
    const intersection = ray.intersectObjects(meshes, false)[0];
    if (!intersection) continue;
    if (hits.some((hit) => Math.abs(hit.column - column) + Math.abs(hit.row - row) <= 2)) continue;
    hits.push({ region_id: region.region_id, label: region.label, index: cell.index, column, row, value: cell.value, count: region.valid_observation_counts[cell.index], point: intersection.point.toArray() });
    if (hits.length >= frame.hotspot_limit) break;
  }
  material.dispose();
  return hits;
}

// inspection-gui/src/three/surfaceShader.ts
import * as T2 from "three";

// config/surface_projection.json
var surface_projection_default = {
  version: "display-template-uv-v2-hvq500",
  scope: "visualization_only_approximate",
  user_authorized_approximate_projection: true,
  default_opacity: 0.88,
  front_facing_cos_min: 0.04,
  zero_signal_opacity: 0.12,
  hotspot_limit: 3,
  hotspot_candidate_limit: 48,
  default: {
    axes: [
      "x",
      "z"
    ],
    normal_sign: 1,
    quarter_turns: 0
  },
  items: {
    toothbrush: {
      axes: [
        "x",
        "y"
      ],
      normal_sign: 1,
      views: {
        C1: 1,
        C2: 1,
        C3: 0,
        C4: 1,
        C5: 0
      }
    },
    zipper: {
      axes: [
        "x",
        "z"
      ],
      normal_sign: 1,
      views: {
        C1: 1,
        C2: 1,
        C3: 0,
        C4: 1,
        C5: 0
      }
    }
  },
  render: {
    contour_levels: [
      0.35,
      0.6,
      0.85
    ],
    contour_width: 0.014,
    fade_start: 0.02,
    fade_end: 0.65,
    low_signal_alpha: 0.04,
    high_signal_alpha: 0.95,
    shape_shading: 0.16,
    bristle_min_alpha: 0.9
  }
};

// inspection-gui/src/three/surfaceShader.ts
function surfaceMaterial(fields, frame, region, filament = false) {
  const style = { ...surface_projection_default.render, ...frame.render };
  return new T2.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    toneMapped: false,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1,
    uniforms: {
      uField: { value: fields.signal },
      uCoverage: { value: fields.mask },
      uOpacity: { value: 1 },
      uLow: { value: new T2.Color(cssVar("--heat-ok")) },
      uMid: { value: new T2.Color(cssVar("--heat-warn")) },
      uHigh: { value: new T2.Color(cssVar("--heat-fail")) },
      uLevels: { value: new T2.Vector3(...style.contour_levels) },
      uContourWidth: { value: style.contour_width },
      uFade: { value: new T2.Vector2(style.fade_start, style.fade_end) },
      uAlpha: { value: new T2.Vector2(filament ? style.bristle_min_alpha : style.low_signal_alpha, style.high_signal_alpha) },
      uShape: { value: style.shape_shading },
      uLowSample: { value: region.sample_products < MIN_DENOMINATOR ? 1 : 0 },
      uResolution: { value: new T2.Vector2(region.grid_width, region.grid_height) }
    },
    vertexShader: `varying vec2 vFieldUv;varying float vShape;
   void main(){vFieldUv=uv;vec3 n=normalize(normalMatrix*normal);vShape=abs(dot(n,normalize(vec3(.25,.4,1.))));gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
    fragmentShader: `uniform sampler2D uField;uniform sampler2D uCoverage;uniform float uOpacity;uniform vec3 uLow;uniform vec3 uMid;uniform vec3 uHigh;
   uniform vec3 uLevels;uniform float uContourWidth;uniform vec2 uFade;uniform vec2 uAlpha;uniform float uShape;uniform float uLowSample;uniform vec2 uResolution;
   varying vec2 vFieldUv;varying float vShape;
   void main(){
    if(texture2D(uCoverage,vFieldUv).r<.5)discard;
    vec4 sampleValue=texture2D(uField,vFieldUv);float value=clamp(sampleValue.r/max(sampleValue.a,.001),0.,1.);
    vec3 color=value<.5?mix(uLow,uMid,value*2.):mix(uMid,uHigh,(value-.5)*2.);
    float distanceToContour=min(abs(value-uLevels.x),min(abs(value-uLevels.y),abs(value-uLevels.z)));
    float contour=1.-smoothstep(uContourWidth*.3,uContourWidth,distanceToContour);
    color=mix(color,uMid,contour*.5);color*=1.-uShape+uShape*vShape;
    float alpha=mix(uAlpha.x,uAlpha.y,smoothstep(uFade.x,uFade.y,value));
    float hatch=mod(floor(vFieldUv.x*uResolution.x)+floor(vFieldUv.y*uResolution.y),4.);
    alpha*=mix(1.,mix(.6,1.,step(1.,hatch)),uLowSample);
    gl_FragColor=vec4(color,alpha*uOpacity);
    #include <colorspace_fragment>
   }`
  });
}

// inspection-gui/src/three/surfaceSdk.ts
function collectRegionMeshes(root) {
  const result = [];
  root.traverse((object) => {
    const mesh = object;
    if (!mesh.isMesh || object.userData.displaySurfaceOverlay) return;
    let owner = object;
    while (owner && !owner.userData.region_id && owner !== root) {
      if (owner.userData.displaySurfaceOverlay) return;
      owner = owner.parent;
    }
    if (typeof owner?.userData.region_id === "string") result.push({ mesh, region_id: owner.userData.region_id, detail_id: object.userData.detail_id });
  });
  return result;
}
function applyDisplaySurface(root, sources, frame, opacity = surface_projection_default.default_opacity) {
  if (frame.scope !== "visualization_only_approximate" || !frame.user_authorized_approximate_projection) throw new Error("Display projection authorization missing");
  root.updateMatrixWorld(true);
  const inverse = root.matrixWorld.clone().invert(), overlay = new T3.Group();
  overlay.name = "display-surface-overlay";
  overlay.userData.displaySurfaceOverlay = true;
  const geometries = [], materials = [], fields = [];
  let disposed = false;
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    root.remove(overlay);
    geometries.forEach((value) => value.dispose());
    materials.forEach((value) => value.dispose());
    fields.forEach((value) => value.dispose());
  };
  const local = sources.map((source) => ({ ...source, geometry: source.mesh.geometry.clone().applyMatrix4(inverse.clone().multiply(source.mesh.matrixWorld)) }));
  const wholeBounds = new T3.Box3();
  local.forEach((source) => {
    source.geometry.computeBoundingBox();
    wholeBounds.union(source.geometry.boundingBox);
  });
  const hotspots = [];
  try {
    const whole = frame.regions.find((region) => region.region_id === "__whole_template__");
    const groups = /* @__PURE__ */ new Map();
    for (const source of local) {
      const list = groups.get(source.region_id) ?? [];
      list.push(source);
      groups.set(source.region_id, list);
    }
    for (const [regionId, parts] of groups) {
      const candidate = frame.regions.find((region2) => region2.region_id === regionId) ?? whole;
      if (!candidate) continue;
      const region = whole ? { ...candidate, region_id: regionId } : candidate, field = surfaceFieldTextures(region);
      if (!field) continue;
      fields.push(field);
      const bounds = whole ? wholeBounds : new T3.Box3();
      if (!whole) parts.forEach((part) => bounds.union(part.geometry.boundingBox));
      const shaders = [surfaceMaterial(field, frame, region), surfaceMaterial(field, frame, region, true)];
      materials.push(...shaders);
      shaders.forEach((shader) => shader.uniforms.uOpacity.value = opacity);
      const projected = [];
      for (const part of parts) {
        const filament = part.detail_id === "bristle-filaments" || part.mesh.userData.surface_role === "bristles";
        const geometry = projectedGeometry(part.geometry, bounds, frame.projection, filament ? -1 : frame.front_facing_cos_min);
        geometries.push(geometry);
        projected.push(geometry);
        const mesh = new T3.Mesh(geometry, shaders[filament ? 1 : 0]);
        mesh.renderOrder = 3;
        mesh.userData = { displaySurfaceOverlay: true, region_id: regionId, source: frame.source, view: frame.view };
        overlay.add(mesh);
      }
      hotspots.push(...mappedHotspots(projected, bounds, frame, region));
    }
    root.add(overlay);
  } catch (error) {
    dispose();
    throw error;
  } finally {
    local.forEach((source) => source.geometry.dispose());
  }
  return { overlay, hotspots, setOpacity: (value) => materials.forEach((material) => material.uniforms.uOpacity.value = T3.MathUtils.clamp(value, 0, 1)), dispose };
}
export {
  applyDisplaySurface,
  collectRegionMeshes,
  mappedHotspots,
  modelUV,
  projectedGeometry,
  sourceToModel,
  surfaceFieldTextures,
  surfaceMaterial
};
