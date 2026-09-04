"""② 분석·구조화 — 자료를 읽고 "어떤 글을 쓸지" 기획안을 만든다 (Claude 호출 1)."""

from __future__ import annotations

from blogwriter.core import llm
from blogwriter.core.backends import Backend
from blogwriter.core.models import Plan, Source, Usage

SYSTEM = "당신은 한국어 블로그 글의 기획을 돕는 편집자다. 요청한 JSON만 정확히 출력한다."


def make_plan(
    backend: Backend,
    source: Source,
    *,
    model: str,
    style_guide: str,
) -> tuple[Plan, Usage]:
    """자료 → 기획안(Plan)."""
    prompt = llm.render(
        llm.load_prompt("plan"),
        style_guide=style_guide,
        source=source.text,
    )
    text, usage = backend.ask(model=model, system=SYSTEM, prompt=prompt, max_tokens=4000)
    plan = Plan.from_dict(llm.parse_json(text))
    if not plan.sections:
        raise llm.LLMError("기획안에 소제목이 하나도 없습니다. 자료가 너무 짧은 것 같습니다.")
    return plan, usage
