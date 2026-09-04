"""Claude에게 물어보는 두 가지 경로.

- ``ClaudeCodeBackend`` (기본): 이미 설치된 ``claude`` CLI를 통해 물어본다.
  **API 키가 필요 없다.** 이미 쓰고 있는 Claude 구독으로 돌아간다.
- ``ApiBackend``: Claude API를 직접 호출한다. ``ANTHROPIC_API_KEY``가 필요하다.

둘 다 같은 ``ask()`` 모양을 가지므로 파이프라인은 어느 쪽인지 몰라도 된다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Protocol

from blogwriter.core.llm import LLMError, estimate_cost
from blogwriter.core.models import Usage


class Backend(Protocol):
    """Claude에게 한 번 물어보고 (텍스트, 사용량)을 돌려주는 것."""

    name: str

    def ask(
        self, *, model: str, system: str, prompt: str, max_tokens: int = 16000
    ) -> tuple[str, Usage]:
        ...


class ClaudeCodeBackend:
    """설치된 ``claude`` CLI로 물어본다. API 키 없이 구독으로 동작한다."""

    name = "claude-code"

    def __init__(self, workdir: Path, *, timeout: int = 900) -> None:
        # 작업 폴더를 고정해 두는 이유가 두 가지 있다.
        #  1) 프로젝트의 CLAUDE.md가 딸려 들어가 글에 섞이는 것을 막는다.
        #  2) 폴더 경로가 프롬프트 앞부분에 들어가므로, 고정해야 캐시가 재사용된다.
        self.workdir = workdir
        self.timeout = timeout

    @staticmethod
    def find_cli() -> str | None:
        """claude 실행 파일 경로. 없으면 None."""
        found = shutil.which("claude")
        if found:
            return found
        fallback = Path.home() / ".local" / "bin" / "claude"
        return str(fallback) if fallback.is_file() else None

    def _command(self, cli: str, model: str, system: str) -> list[str]:
        return [
            cli,
            "-p",                        # 대화형이 아니라 한 번 답하고 끝
            "--output-format", "json",   # 사용량까지 받기 위해
            "--model", model,
            "--system-prompt", system,
            "--allowed-tools", "",       # 글만 쓰면 되므로 도구는 전부 끔
            "--disable-slash-commands",
            "--strict-mcp-config",       # 사용자의 MCP 서버(노션 등)를 붙이지 않음
        ]

    def ask(
        self, *, model: str, system: str, prompt: str, max_tokens: int = 16000
    ) -> tuple[str, Usage]:
        cli = self.find_cli()
        if cli is None:
            raise LLMError(
                "Claude Code(claude 명령)를 찾을 수 없습니다.\n"
                "  터미널에서 `claude --version` 이 되는지 확인하세요.\n"
                "  설치돼 있는데도 안 되면 터미널을 껐다 켜 보세요."
            )

        self.workdir.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                self._command(cli, model, system),
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.workdir,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LLMError(
                f"Claude 응답이 {self.timeout}초 안에 오지 않았습니다. "
                "자료를 줄여서 다시 시도해 보세요."
            ) from exc

        payload = _last_result_json(result.stdout)
        if payload is None:
            detail = (result.stderr or result.stdout or "").strip()[:400]
            raise LLMError(
                "Claude Code 실행에 실패했습니다.\n"
                f"  {detail or '알 수 없는 오류'}\n"
                "  터미널에서 `claude` 를 한 번 실행해 로그인 상태를 확인해 보세요."
            )

        if payload.get("is_error") or payload.get("subtype") != "success":
            raise LLMError(
                "Claude가 요청을 끝내지 못했습니다: "
                f"{payload.get('result') or payload.get('subtype') or '알 수 없는 이유'}"
            )

        text = str(payload.get("result", "")).strip()
        if not text:
            raise LLMError("Claude가 빈 응답을 돌려줬습니다. 자료가 너무 짧지 않은지 확인하세요.")

        return text, _usage_from_cli(payload)


class ApiBackend:
    """Claude API를 직접 호출한다. ANTHROPIC_API_KEY가 필요하다."""

    name = "api"

    def __init__(self, client: object | None = None) -> None:
        self._client = client

    @property
    def client(self):  # noqa: ANN201 - anthropic 타입을 지연 임포트한다
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def ask(
        self, *, model: str, system: str, prompt: str, max_tokens: int = 16000
    ) -> tuple[str, Usage]:
        import anthropic

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.AuthenticationError as exc:
            raise LLMError("API 키가 올바르지 않습니다. ANTHROPIC_API_KEY를 확인하세요.") from exc
        except anthropic.RateLimitError as exc:
            raise LLMError("요청이 몰려 잠시 거부됐습니다. 1~2분 뒤 다시 시도하세요.") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("네트워크 연결에 실패했습니다. 인터넷 상태를 확인하세요.") from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Claude API 오류({exc.status_code}): {exc.message}") from exc

        text = "\n".join(b.text for b in response.content if b.type == "text").strip()
        if not text:
            raise LLMError("Claude가 빈 응답을 돌려줬습니다. 자료가 너무 짧지 않은지 확인하세요.")

        usage = Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=estimate_cost(
                model, response.usage.input_tokens, response.usage.output_tokens
            ),
        )
        return text, usage


def _last_result_json(stdout: str) -> dict | None:
    """CLI 출력에서 마지막 결과 JSON을 찾는다.

    경고 줄이 앞에 섞여 나오는 경우가 있어 줄 단위로 훑는다.
    """
    found: dict | None = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("type") == "result":
            found = parsed
    return found


def _usage_from_cli(payload: dict) -> Usage:
    """CLI가 돌려준 사용량을 Usage로 옮긴다."""
    usage = payload.get("usage") or {}
    read = int(usage.get("cache_read_input_tokens", 0) or 0)
    created = int(usage.get("cache_creation_input_tokens", 0) or 0)
    return Usage(
        input_tokens=int(usage.get("input_tokens", 0) or 0) + read + created,
        output_tokens=int(usage.get("output_tokens", 0) or 0),
        cost_usd=float(payload.get("total_cost_usd", 0.0) or 0.0),
    )
