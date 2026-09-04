"""CLI 뼈대가 정상 동작하는지 확인하는 스모크 테스트."""

import pytest
from typer.testing import CliRunner

from blogwriter import __version__
from blogwriter.cli import app
from blogwriter.publish import clipboard

runner = CliRunner()


@pytest.fixture(autouse=True)
def empty_clipboard(monkeypatch):
    """테스트가 실수로 진짜 Claude를 부르지 않도록 클립보드를 비워 둔다.

    `blog write` 는 옵션이 없으면 클립보드를 읽으므로, 막아 두지 않으면
    테스트가 실제 글 생성을 시작해 버린다.
    """
    monkeypatch.setattr(clipboard, "read_plain", lambda: "")


def test_help_shows_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("write", "plan", "list", "publish", "config"):
        assert command in result.stdout


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_unimplemented_command_exits_with_error() -> None:
    # plan 은 아직 Phase 2 대기 상태다
    result = runner.invoke(app, ["plan"])
    assert result.exit_code == 1
    assert "아직 만들지 않은" in result.stdout


def test_write_without_material_explains_how_to_copy() -> None:
    """자료가 없으면 Claude를 부르지 않고 복사 방법을 안내해야 한다."""
    result = runner.invoke(app, ["write"])
    assert result.exit_code == 1
    assert "복사" in result.output
    assert "⌘+C" in result.output


def test_write_rejects_too_short_material() -> None:
    result = runner.invoke(app, ["write", "--text", "짧은 자료"])
    assert result.exit_code == 1
    assert "너무 짧습니다" in result.output
