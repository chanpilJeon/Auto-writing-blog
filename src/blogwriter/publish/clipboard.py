"""클립보드에 서식 있는 HTML을 넣는다.

일반 복사(pyperclip)는 평문만 담기 때문에 블로그 에디터에 붙여 넣으면 서식이 사라진다.
macOS에서는 osascript로 클립보드에 ``«class HTML»`` 플레이버를 직접 심어야
소제목·굵게·링크가 살아 있는 상태로 붙여넣기가 된다.
"""

from __future__ import annotations

import platform
import subprocess


class ClipboardError(Exception):
    """클립보드에 넣지 못했을 때."""


def is_macos() -> bool:
    return platform.system() == "Darwin"


def _hex(text: str, encoding: str) -> str:
    return text.encode(encoding).hex()


def copy_rich(html: str, plain: str) -> None:
    """HTML(서식)과 평문을 함께 클립보드에 넣는다.

    붙여넣는 곳이 서식을 받으면 HTML이, 평문만 받으면 평문이 들어간다.
    """
    if not is_macos():
        copy_plain(plain)
        return

    script = (
        "set the clipboard to {"
        f"«class HTML»:«data HTML{_hex(html, 'utf-8')}», "
        f"«class ut16»:«data ut16{_hex(plain, 'utf-16-be')}»"
        "}"
    )
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ClipboardError(
            "클립보드에 복사하지 못했습니다.\n"
            f"  {result.stderr.strip()}\n"
            "  --format text 옵션으로 평문 복사를 시도해 보세요."
        )


def copy_plain(text: str) -> None:
    """평문만 클립보드에 넣는다."""
    try:
        import pyperclip

        pyperclip.copy(text)
    except Exception as exc:  # noqa: BLE001 - 플랫폼마다 실패 이유가 제각각이다
        raise ClipboardError(f"클립보드에 복사하지 못했습니다: {exc}") from exc
