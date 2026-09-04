"""④ 다듬기 — 본문에서 제목 후보·태그·메타 설명을 뽑는다 (Claude 호출 3)."""

from __future__ import annotations

import anthropic

from blogwriter.core import llm
from blogwriter.core.models import Draft, Polish, Usage

SYSTEM = "당신은 한국어 블로그 편집자다. 요청한 JSON만 정확히 출력한다."


def polish(
    client: anthropic.Anthropic,
    draft: Draft,
    *,
    model: str,
    style_guide: str,
) -> tuple[Polish, Usage]:
    """본문 → 제목 후보·태그·메타 설명(Polish)."""
    prompt = llm.render(
        llm.load_prompt("polish"),
        style_guide=style_guide,
        body=draft.body,
    )
    text, usage = llm.ask(client, model=model, system=SYSTEM, prompt=prompt, max_tokens=2000)
    return Polish.from_dict(llm.parse_json(text)), usage
