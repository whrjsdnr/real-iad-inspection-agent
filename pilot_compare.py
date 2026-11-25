"""파일럿 비교 — 동일 제품의 저장 점수로 레거시 규칙 vs 도출 규칙 판정 분포 비교.

  inference/.venv/bin/python pilot_compare.py [--limit 100]

배치(batch_fusion.py)가 fusion-v2 태그로 기록한 findings에서 뷰 점수를 읽어
  - 레거시: RT 박스(≥0.4) 존재 + hvq ≥ 임계값(교정 파일) → both/disagree 규칙
  - 도출:   fusion_score 메타 + TH±margin
두 판정을 비교한다(재추론 없음).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENT_ROOT))
sys.path.insert(0, str(AGENT_ROOT.parent / "MV"))

import fusion  # noqa: E402

RUN_TAG = "fusion-v2:rtdetr-epoch15-fp32+hvq-best-fp16"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(AGENT_ROOT / "inspection.db"))
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args(argv)

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    ck = fusion.load_hvq_thresholds(AGENT_ROOT.parent / "MV" / "hvq_best.pt")
    legacy_thr, _ = fusion.merge_thresholds(ck, AGENT_ROOT / "config" / "hvq_thresholds.json")
    derived = fusion.load_derived()
    if derived is None:
        print("[compare] 도출 설정 없음 — derive_fusion.py 먼저 실행")
        return 2

    products = con.execute(
        "SELECT * FROM inspection_attempts WHERE model_version=? AND status='completed' "
        "ORDER BY product_id LIMIT ?", (RUN_TAG, args.limit)).fetchall()
    rows = {r["product_id"]: dict(r) for r in products}

    findings = con.execute(
        "SELECT * FROM findings WHERE product_id IN (%s)"
        % ",".join("?" * len(rows)), list(rows)).fetchall()

    views: dict[str, dict] = {pid: {} for pid in rows}
    for f in findings:
        v = views[f["product_id"]].setdefault(f["camera_id"], {"rt": 0.0, "hvq": 0.0, "meta": None})
        if f["kind"] == "rtdetr_box":
            v["rt"] = max(v["rt"], f["score"])
        elif f["kind"] == "hvq_score":
            v["hvq"] = max(v["hvq"], f["score"])
            v["meta"] = json.loads(f["meta_json"]) if f["meta_json"] else None

    rt_conf_floor = 0.4
    stats = {"legacy": {}, "derived": {}, "cross": {}}
    for pid, p in rows.items():
        vv = views.get(pid, {})
        rt_pos = any(x["rt"] >= rt_conf_floor for x in vv.values())
        hvq_max = max((x["hvq"] for x in vv.values()), default=0.0)
        l_verdict = fusion.decide(rt_pos, hvq_max >= legacy_thr.get(p["item"], 81.0),
                                  {"both_positive": "defect", "both_negative": "normal",
                                   "disagree": "hold", "hvq_positive_only": "hold",
                                   "rtdetr_positive_only": "hold"})
        d_verdict = p["verdict"]
        meta0 = next((x["meta"] for x in vv.values() if x["meta"]), {})
        fscore = meta0.get("fusion_score")
        if fscore is not None:
            th, margin = derived["derived"]["th"], derived["derived"]["margin"]
            d_verdict = ("defect" if fscore >= th + margin
                         else "normal" if fscore <= th - margin else "hold")
        for tag, vd in (("legacy", l_verdict), ("derived", d_verdict)):
            stats[tag][vd] = stats[tag].get(vd, 0) + 1
        key = (l_verdict, d_verdict)
        stats["cross"][key] = stats["cross"].get(key, 0) + 1

    n = len(rows)
    print(f"[compare] 제품 {n}개 — 레거시 vs 도출 규칙 판정 분포")
    for tag in ("legacy", "derived"):
        dist = stats[tag]
        print(f"  {tag:8s}: " + ", ".join(f"{k}={dist.get(k,0)} ({dist.get(k,0)/n:.0%})"
                                          for k in ("normal", "defect", "hold")))
    print("  전환(legacy→derived):")
    for (l, d), c in sorted(stats["cross"].items(), key=lambda x: -x[1]):
        if l != d:
            print(f"    {l:6s} → {d:6s}: {c}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
