"""③ 초안 작성 — 기획안 + 스타일 가이드로 본문을 쓴다 (Claude 호출 2)."""

from __future__ import annotations

from blogwriter.core import llm
from blogwriter.core.backends import Backend
from blogwriter.core.models import Draft, Plan, Source, Usage

SYSTEM = (
    "당신은 주어진 스타일 가이드를 쓴 사람의 글투를 그대로 흉내 내어 한국어 블로그 본문을 쓴다. "
    "마크다운 본문만 출력하고 다른 말은 붙이지 않는다."
)


def _format_outline(plan: Plan) -> str:
    lines: list[str] = []
    for index, section in enumerate(plan.sections, start=1):
        lines.append(f"{index}. {section.heading}")
        lines.extend(f"   - {point}" for point in section.points)
    return "\n".join(lines) if lines else "(없음)"


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "(없음)"


def write_draft(
    backend: Backend,
    source: Source,
    plan: Plan,
    *,
    model: str,
    style_guide: str,
) -> tuple[Draft, Usage]:
    """기획안 → 본문 초안(Draft)."""
    prompt = llm.render(
        llm.load_prompt("write"),
        style_guide=style_guide,
        angle=plan.angle or "(지정 없음)",
        target_reader=plan.target_reader or "(지정 없음)",
        outline=_format_outline(plan),
        key_facts=_bullets(plan.key_facts),
        cautions=_bullets(plan.cautions),
        source=source.text,
    )
    text, usage = backend.ask(model=model, system=SYSTEM, prompt=prompt, max_tokens=16000)
    return Draft(body=llm.strip_code_fence(text)), usage
