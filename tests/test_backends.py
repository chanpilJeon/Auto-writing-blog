"""Claude Code 백엔드 테스트 (실제 claude 호출 없음)."""

from __future__ import annotations

import json
import subprocess

import pytest

from blogwriter.core import backends
from blogwriter.core.backends import ClaudeCodeBackend
from blogwriter.core.llm import LLMError


def _cli_payload(result: str, **overrides) -> str:
    payload = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": result,
        "total_cost_usd": 0.0115,
        "usage": {
            "input_tokens": 2,
            "cache_creation_input_tokens": 1560,
            "cache_read_input_tokens": 25563,
            "output_tokens": 300,
        },
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


@pytest.fixture
def stub_cli(monkeypatch, tmp_path):
    """claude 실행 파일이 있는 것처럼 만들고, 실행 결과를 가로챈다."""
    monkeypatch.setattr(ClaudeCodeBackend, "find_cli", staticmethod(lambda: "/usr/bin/claude"))
    box: dict = {}

    def fake_run(cmd, **kwargs):
        box["cmd"] = cmd
        box["input"] = kwargs.get("input")
        box["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(cmd, 0, box.get("stdout", ""), box.get("stderr", ""))

    monkeypatch.setattr(subprocess, "run", fake_run)
    return box


def test_ask_returns_text_and_usage(stub_cli, tmp_path):
    stub_cli["stdout"] = _cli_payload("본문이다")
    backend = ClaudeCodeBackend(tmp_path / "work")

    text, usage = backend.ask(model="claude-sonnet-5", system="시스템", prompt="프롬프트")

    assert text == "본문이다"
    # 입력 토큰은 캐시 생성·읽기까지 합산한다
    assert usage.input_tokens == 2 + 1560 + 25563
    assert usage.output_tokens == 300
    assert usage.cost_usd == pytest.approx(0.0115)


def test_command_disables_tools_and_mcp(stub_cli, tmp_path):
    stub_cli["stdout"] = _cli_payload("ok")
    workdir = tmp_path / "work"
    ClaudeCodeBackend(workdir).ask(model="claude-opus-5", system="시스템", prompt="프롬프트")

    cmd = stub_cli["cmd"]
    assert "-p" in cmd and "--strict-mcp-config" in cmd and "--disable-slash-commands" in cmd
    assert cmd[cmd.index("--model") + 1] == "claude-opus-5"
    assert cmd[cmd.index("--system-prompt") + 1] == "시스템"
    # 도구는 전부 끈다
    assert cmd[cmd.index("--allowed-tools") + 1] == ""
    # 프롬프트는 인자가 아니라 표준입력으로 넘긴다 (길이 제한 회피)
    assert stub_cli["input"] == "프롬프트"
    # 프로젝트 CLAUDE.md가 딸려 들어가지 않도록 전용 폴더에서 실행한다
    assert stub_cli["cwd"] == workdir
    assert workdir.is_dir()


def test_warning_lines_before_json_are_ignored(stub_cli, tmp_path):
    stub_cli["stdout"] = "경고: 무언가\n" + _cli_payload("본문")
    text, _ = ClaudeCodeBackend(tmp_path / "w").ask(model="m", system="s", prompt="p")
    assert text == "본문"


def test_missing_cli_gives_friendly_error(monkeypatch, tmp_path):
    monkeypatch.setattr(ClaudeCodeBackend, "find_cli", staticmethod(lambda: None))
    with pytest.raises(LLMError, match="claude 명령"):
        ClaudeCodeBackend(tmp_path / "w").ask(model="m", system="s", prompt="p")


def test_unparseable_output_raises(stub_cli, tmp_path):
    stub_cli["stdout"] = "그냥 텍스트"
    stub_cli["stderr"] = "로그인이 필요합니다"
    with pytest.raises(LLMError, match="로그인이 필요합니다"):
        ClaudeCodeBackend(tmp_path / "w").ask(model="m", system="s", prompt="p")


def test_error_payload_raises(stub_cli, tmp_path):
    stub_cli["stdout"] = _cli_payload("한도 초과", is_error=True, subtype="error_max_turns")
    with pytest.raises(LLMError, match="한도 초과"):
        ClaudeCodeBackend(tmp_path / "w").ask(model="m", system="s", prompt="p")


def test_timeout_gives_friendly_error(monkeypatch, tmp_path):
    monkeypatch.setattr(ClaudeCodeBackend, "find_cli", staticmethod(lambda: "/usr/bin/claude"))

    def raise_timeout(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 900)

    monkeypatch.setattr(subprocess, "run", raise_timeout)
    with pytest.raises(LLMError, match="900초"):
        ClaudeCodeBackend(tmp_path / "w").ask(model="m", system="s", prompt="p")


def test_last_result_json_picks_result_type():
    stdout = '{"type":"system"}\n{"type":"result","result":"A"}\n'
    assert backends._last_result_json(stdout)["result"] == "A"
    assert backends._last_result_json("아무것도 없음") is None
