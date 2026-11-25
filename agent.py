"""Ollama Qwen 로컬 모델 기반 제조 외관검사 LLM 에이전트.

LLM은 SQL을 직접 만들지 않고 app.tools의 검증된 도구 4개만 호출한다.
외부 LLM API를 쓰지 않는다 (base_url은 로컬 Ollama).
"""
import json
import os
import sys

from openai import OpenAI

from app.tools import TOOL_FUNCS, TOOL_SCHEMAS
# LLM 권한은 조회·검수 요청 네 종류로 제한한다. GUI 승인 API는 별도 유지한다.
LLM_TOOL_NAMES = frozenset({"query_error_stats", "get_case_evidence", "request_review", "get_training_status", "get_final_performance", "query_spatial_evidence"})
TOOL_FUNCS = {k:v for k,v in TOOL_FUNCS.items() if k in LLM_TOOL_NAMES}
TOOL_SCHEMAS = [s for s in TOOL_SCHEMAS if s["function"]["name"] in LLM_TOOL_NAMES]


client = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    api_key="ollama",
)
MODEL = os.getenv("OLLAMA_MODEL", "qwen25-cpu")


def detect_mode() -> str:
    """Ollama 연결 확인. 안 되면 mock."""
    if os.getenv("AGENT_MOCK", "") == "1":
        return "mock"
    try:
        import urllib.request  # noqa: PLC0415

        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").replace("/v1", "")
        with urllib.request.urlopen(f"{base}/api/tags", timeout=3) as r:
            return "real" if r.status == 200 else "mock"
    except Exception:  # noqa: BLE001
        return "mock"


MODE = detect_mode()

SYSTEM_PROMPT = (
    "짧게 답하고, 통계는 반드시 도구에서 받은 분자/분모와 함께 설명한다. "
    "검수 확정 전과 후를 섞지 않는다. 도구 조회 없이 수치를 추측하지 않는다."
)
MAX_TOOL_CALLS = 5
TOOL_RESULT_MAX_CHARS = 4000


def mock_answer(question: str) -> str:
    """목 모드: 도구를 실제로 호출해 근거 있는 답변을 생성한다(LLM 없음)."""
    from migrate import migrate
    migrate()
    q = question.lower()
    item = "toothbrush" if ("칫솔" in question or "toothbrush" in q) else None
    lines = ["[목 모드] Ollama에 연결할 수 없어 도구 직접 조회 결과로 답합니다."]
    if any(k in q for k in ["미탐", "miss", "통계", "지표", "오류"]):
        metric = "part_miss_rate" if ("미탐" in q or "miss" in q) else "part_miss_rate"
        r = TOOL_FUNCS["query_error_stats"](
            item=item or "toothbrush", metric=metric, group_by=["part_id"])
        lines.append(f"부위 미탐률 집계(품목={r.get('item', item or 'toothbrush')}, 지표={r.get('metric', metric)}, "
                     f"검수=confirmed):")
        for row in r.get("rows", [])[:5]:
            den = row.get("den", 0)
            rate_txt = f"{row['rate']:.1%}" if den and row.get("rate") is not None else "분모 0"
            part = row.get("group", {}).get("part_id", "?")
            lines.append(f"  - {part}: {row.get('num', 0)}/{den} ({rate_txt})")
        if not r.get("rows"):
            lines.append("  (해당 지표의 검수 확정 사례가 없어 분모 0 — 미탐률을 계산할 수 없습니다)")
        return "\n".join(lines)
    if any(k in q for k in ["최종", "성능", "f1", "auroc", "fp", "fn"]):
        r = TOOL_FUNCS["get_final_performance"](item=item)
        if not r.get("available"):
            lines.append(f"최종 성능 산출 상태: {r.get('state', 'waiting')} "
                         f"(전체 추론·DB 반영·에이전트 검증 완료 후 산출됩니다)")
            return "\n".join(lines)
        m = r["metrics"] or {}
        b = r["baseline_v1"] or {}
        def fmt(v):
            return f"{v:.4f}" if isinstance(v, float) else str(v)
        lines.append(
            f"최종 성능({r.get('model_version')}, 실데이터 전체): "
            f"F1={fmt(m.get('f1_micro'))} (기준선 v1 {b.get('f1')}), "
            f"Recall={fmt(m.get('recall'))} (기준선 {b.get('recall')}), "
            f"AUROC={fmt(m.get('auroc'))}, "
            f"FP={m.get('fp')}, FN={m.get('fn')}, "
            f"보류 {m.get('hold_products')}건({fmt(m.get('hold_rate'))})")
        lines.append(f"검증: 독립 SQL·에이전트 도구 교차확인 "
                     f"{'완료' if m.get('verified') else '미완'} · 리포트 {r.get('report_path')}")
        return "\n".join(lines)
    if any(k in q for k in ["학습", "상태", "표본"]):
        r = TOOL_FUNCS["get_training_status"](item=item)
        lines.append(f"승인 표본 {r['approved_samples']['num']}개 / "
                     f"검수 대기 {r['pending_candidates']['num']}개 / "
                     f"보류 후보 {r['hold_candidates']['num']}개")
        return "\n".join(lines)
    r = TOOL_FUNCS["get_training_status"](item=item)
    lines.append(f"요약: 확정 {r['approved_samples']['num']}, 대기 {r['pending_candidates']['num']}, "
                 f"보류 {r['hold_candidates']['num']}. 구체 질문(미탐/통계/학습 상태)을 시도하세요.")
    return "\n".join(lines)


def run_tool(name: str, args: dict) -> str:
    fn = TOOL_FUNCS.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)
    try:
        result = fn(**args)
        text = json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:  # ToolError 포함 - LLM이 다음 행동을 고르게 내용만 전달
        text = json.dumps({"error": str(e)}, ensure_ascii=False)
    return text[:TOOL_RESULT_MAX_CHARS]


def chat(question: str) -> str | None:
    if MODE == "mock":
        answer = mock_answer(question)
        print(answer)
        return answer
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    for _ in range(MAX_TOOL_CALLS):
        r = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
        )
        m = r.choices[0].message
        messages.append(m)

        if not m.tool_calls:
            print(m.content)
            return m.content

        for c in m.tool_calls:
            args = json.loads(c.function.arguments or "{}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": c.id,
                    "name": c.function.name,
                    "content": run_tool(c.function.name, args),
                }
            )
    print("도구 호출 한도(5회)에 도달해 중단합니다.")
    return None


def main() -> None:
    if MODE == "mock":
        print("*** 목 모드 (Ollama 미연결, 도구 직접 조회) ***")
    if len(sys.argv) > 1:
        chat(" ".join(sys.argv[1:]))
        return
    print("제조 외관검사 에이전트 - 질문을 입력하세요. (quit: 종료)")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q.lower() in {"q", "quit", "exit"}:
            break
        chat(q)


if __name__ == "__main__":
    main()
