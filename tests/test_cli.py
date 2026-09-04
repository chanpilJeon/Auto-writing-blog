"""CLI 뼈대가 정상 동작하는지 확인하는 스모크 테스트."""

from typer.testing import CliRunner

from blogwriter import __version__
from blogwriter.cli import app

runner = CliRunner()


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
    result = runner.invoke(app, ["write"])
    assert result.exit_code == 1
