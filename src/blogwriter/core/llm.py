"""프롬프트와 응답을 다루는 공용 유틸.

planner / writer / polisher가 공통으로 쓰는 것:
- 프롬프트 템플릿 로드 (``prompts/*.md``)
- 모델이 돌려준 JSON·마크다운을 안전하게 파싱
- 토큰 수 → 비용 환산

실제 Claude 호출은 ``core/backends.py``가 맡는다.
"""

from __future__ import annotations

import json
import re
from importlib import resources

# 1M 토큰당 달러 (입력, 출력). 모르는 모델은 비용 0으로 둔다.
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


class LLMError(Exception):
    """Claude 호출 또는 응답 해석에 실패했을 때."""


def load_prompt(name: str) -> str:
    """``prompts/<name>.md`` 템플릿을 읽는다."""
    return resources.files("blogwriter.prompts").joinpath(f"{name}.md").read_text(
        encoding="utf-8"
    )


def render(template: str, **values: str) -> str:
    """템플릿의 ``{{KEY}}`` 자리를 값으로 치환한다.

    마크다운 본문에 중괄호가 섞여도 안전하도록 str.format 대신 단순 치환을 쓴다.
    """
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key.upper() + "}}", value)
    return out


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """토큰 수로 대략적인 비용(USD)을 계산한다."""
    price_in, price_out = PRICING.get(model, (0.0, 0.0))
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_json(text: str) -> dict:
    """모델 응답에서 JSON 객체를 뽑아낸다.

    ```json 코드펜스로 감싸 오거나 앞뒤에 설명을 붙여 오는 경우까지 처리한다.
    """
    candidates = [text]
    match = _JSON_BLOCK.search(text)
    if match:
        candidates.insert(0, match.group(1))
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise LLMError("Claude 응답을 JSON으로 읽지 못했습니다. 다시 실행해 보세요.")


def strip_code_fence(text: str) -> str:
    """본문 전체가 ```markdown ... ``` 로 감싸져 온 경우 펜스를 벗긴다."""
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return stripped
