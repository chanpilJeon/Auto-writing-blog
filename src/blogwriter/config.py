"""설정 파일(config.toml)과 API 키를 다루는 모듈.

- 설정 위치: ``~/.config/blogwriter/config.toml``
- API 키는 설정 파일에 저장하지 않고 환경변수 ``ANTHROPIC_API_KEY``에서만 읽는다.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("BLOGWRITER_CONFIG_DIR", "~/.config/blogwriter")).expanduser()
CONFIG_PATH = CONFIG_DIR / "config.toml"
STYLE_GUIDE_PATH = CONFIG_DIR / "style-guide.md"
DATA_DIR = Path(
    os.environ.get("BLOGWRITER_DATA_DIR", "~/.local/share/blogwriter")
).expanduser()

DEFAULT_CONFIG_TOML = f"""\
[model]
plan = "claude-sonnet-5"
write = "claude-sonnet-5"    # 품질이 아쉬우면 "claude-opus-5"로 교체
polish = "claude-sonnet-5"

[output]
drafts_dir = "~/BlogDrafts"

[style]
guide = "{STYLE_GUIDE_PATH}"
"""


class ConfigError(Exception):
    """설정이 잘못됐거나 API 키가 없을 때."""


@dataclass(frozen=True)
class Config:
    """실행에 필요한 설정 한 벌."""

    plan_model: str = "claude-sonnet-5"
    write_model: str = "claude-sonnet-5"
    polish_model: str = "claude-sonnet-5"
    drafts_dir: Path = field(default_factory=lambda: Path("~/BlogDrafts").expanduser())
    style_guide_path: Path = field(default_factory=lambda: STYLE_GUIDE_PATH)

    @property
    def style_guide(self) -> str:
        """스타일 가이드 본문. 파일이 없으면 기본 템플릿을 돌려준다."""
        if self.style_guide_path.is_file():
            return self.style_guide_path.read_text(encoding="utf-8")
        return default_style_guide()


def default_style_guide() -> str:
    """패키지에 동봉된 기본 스타일 가이드 원문."""
    return resources.files("blogwriter.prompts").joinpath("style-guide.md").read_text(
        encoding="utf-8"
    )


def ensure_files() -> tuple[Path, Path]:
    """설정 파일과 스타일 가이드가 없으면 기본값으로 만든다.

    Returns:
        (config.toml 경로, style-guide.md 경로)
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")
    if not STYLE_GUIDE_PATH.exists():
        STYLE_GUIDE_PATH.write_text(default_style_guide(), encoding="utf-8")
    return CONFIG_PATH, STYLE_GUIDE_PATH


def load() -> Config:
    """설정 파일을 읽어 Config를 만든다. 파일이 없으면 기본값으로 생성한다."""
    ensure_files()
    raw = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    model = raw.get("model", {})
    output = raw.get("output", {})
    style = raw.get("style", {})

    default = "claude-sonnet-5"
    return Config(
        plan_model=model.get("plan", default),
        write_model=model.get("write", default),
        polish_model=model.get("polish", default),
        drafts_dir=Path(output.get("drafts_dir", "~/BlogDrafts")).expanduser(),
        style_guide_path=Path(style.get("guide", STYLE_GUIDE_PATH)).expanduser(),
    )


def api_key() -> str:
    """환경변수에서 Claude API 키를 읽는다. 없으면 안내와 함께 예외."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ConfigError(
            "ANTHROPIC_API_KEY 환경변수가 없습니다.\n"
            "  1) https://console.anthropic.com 에서 API 키를 발급받고\n"
            "  2) 터미널에서 아래를 실행한 뒤 터미널을 새로 여세요:\n"
            "     echo 'export ANTHROPIC_API_KEY=\"sk-ant-여기에키\"' >> ~/.zshrc"
        )
    return key
