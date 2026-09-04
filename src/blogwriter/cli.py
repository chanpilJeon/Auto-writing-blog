"""Typer CLI 진입점.

파이프라인 본체는 ``blogwriter.core`` 안에 있고, 이 파일은 그것을 터미널에
연결하는 얇은 껍데기다. (CLI ↔ core 분리 — ToDo.md §2 설계 원칙)
"""

from __future__ import annotations

import typer

from blogwriter import __version__

app = typer.Typer(
    name="blog",
    help="정보(URL·텍스트·파일)를 받아 내 말투의 블로그 글 초안을 만들어 주는 도구.",
    no_args_is_help=True,
    add_completion=False,
)


def _not_implemented(step: str) -> None:
    typer.secho(f"아직 만들지 않은 기능입니다: {step}", fg=typer.colors.YELLOW)
    typer.echo("→ ToDo.md의 다음 Phase에서 구현될 예정입니다.")
    raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """설치된 blogwriter 버전을 출력한다."""
    typer.echo(f"blogwriter {__version__}")


@app.command()
def config() -> None:
    """설정 파일 위치와 현재 설정값을 보여준다."""
    _not_implemented("blog config (Phase 1)")


@app.command()
def write() -> None:
    """자료를 받아 블로그 글 초안을 작성한다."""
    _not_implemented("blog write (Phase 1)")


@app.command(name="list")
def list_runs() -> None:
    """지금까지 생성한 글 이력을 보여준다."""
    _not_implemented("blog list (Phase 1)")


@app.command()
def plan() -> None:
    """글의 각도와 목차(기획안)까지만 만든다."""
    _not_implemented("blog plan (Phase 2)")


@app.command()
def resume() -> None:
    """저장된 기획안으로 본문 작성을 이어서 한다."""
    _not_implemented("blog resume (Phase 2)")


@app.command()
def publish() -> None:
    """완성된 글을 발행(또는 클립보드 복사)한다."""
    _not_implemented("blog publish (Phase 3)")


if __name__ == "__main__":
    app()
