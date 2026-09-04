"""테스트 공통 준비물 — 가짜 Claude 클라이언트와 임시 폴더."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from blogwriter import config as config_module
from blogwriter.config import Config
from blogwriter.core.models import Usage

PLAN_JSON = {
    "working_title": "임시 제목",
    "angle": "이 자료의 핵심은 비용 구조다",
    "target_reader": "개인 개발 도구를 만드는 사람",
    "sections": [
        {"heading": "무엇이 달라졌나", "points": ["요점 A", "요점 B"]},
        {"heading": "왜 중요한가", "points": ["요점 C"]},
        {"heading": "남는 질문", "points": ["요점 D"]},
    ],
    "key_facts": ["가격은 100원이다"],
    "cautions": ["단정하지 말 것"],
}

DRAFT_BODY = "## 무엇이 달라졌나\n\n본문이다.\n\n## 왜 중요한가\n\n또 본문이다.\n"

POLISH_JSON = {
    "titles": ["첫 번째 제목", "두 번째 제목", "세 번째 제목"],
    "tags": ["블로그", "자동화", "CLI"],
    "description": "이 글은 자동 작성 도구에 대해 다룬다.",
}


class FakeBackend:
    """Claude를 부르지 않고 미리 정해 둔 답을 순서대로 돌려주는 가짜 백엔드."""

    name = "fake"

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[dict] = []

    def ask(
        self, *, model: str, system: str, prompt: str, max_tokens: int = 16000
    ) -> tuple[str, Usage]:
        self.calls.append(
            {"model": model, "system": system, "prompt": prompt, "max_tokens": max_tokens}
        )
        if not self._replies:
            raise AssertionError("예상보다 많은 Claude 호출이 일어났습니다.")
        return self._replies.pop(0), Usage(input_tokens=1000, output_tokens=500, cost_usd=0.01)


@pytest.fixture
def fake_backend() -> FakeBackend:
    return FakeBackend(
        [
            json.dumps(PLAN_JSON, ensure_ascii=False),
            DRAFT_BODY,
            json.dumps(POLISH_JSON, ensure_ascii=False),
        ]
    )


@pytest.fixture
def make_backend_with():
    """원하는 응답을 주는 가짜 백엔드를 만들어 주는 팩토리."""
    return FakeBackend


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    """설정·DB·글 저장 폴더를 모두 임시 디렉터리로 돌린다."""
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config" / "config.toml")
    monkeypatch.setattr(config_module, "STYLE_GUIDE_PATH", tmp_path / "config" / "style-guide.md")
    monkeypatch.setattr(config_module, "DATA_DIR", tmp_path / "data")
    return Config(
        drafts_dir=tmp_path / "drafts",
        style_guide_path=tmp_path / "config" / "style-guide.md",
    )
