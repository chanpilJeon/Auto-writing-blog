"""Typer CLI 진입점.

파이프라인 본체는 ``blogwriter.core`` 안에 있고, 이 파일은 그것을 터미널에
연결하는 얇은 껍데기다. (CLI ↔ core 분리 — ToDo.md §2 설계 원칙)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from blogwriter import __version__
from blogwriter import config as config_module
from blogwriter.core.llm import LLMError
from blogwriter.core.models import Source
from blogwriter.core.pipeline import run as run_pipeline
from blogwriter.store import db

app = typer.Typer(
    name="blog",
    help="정보(URL·텍스트·파일)를 받아 내 말투의 블로그 글 초안을 만들어 주는 도구.",
    no_args_is_help=True,
    add_completion=False,
)


def _die(message: str) -> None:
    """에러 메시지를 붉게 찍고 종료한다."""
    typer.secho(f"\n[실패] {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


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
    config_path, style_path = config_module.ensure_files()
    settings = config_module.load()

    typer.secho("설정", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"  설정 파일       {config_path}")
    typer.echo(f"  스타일 가이드   {style_path}")
    typer.echo(f"  글 저장 폴더    {settings.drafts_dir}")
    typer.echo(f"  이력 DB         {db.db_path()}")
    typer.echo("")
    typer.secho("사용 모델", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"  기획   {settings.plan_model}")
    typer.echo(f"  작성   {settings.write_model}")
    typer.echo(f"  다듬기 {settings.polish_model}")
    typer.echo("")

    try:
        key = config_module.api_key()
        typer.secho(f"API 키  설정됨 ({key[:10]}...)", fg=typer.colors.GREEN)
    except config_module.ConfigError as exc:
        typer.secho("API 키  없음", fg=typer.colors.RED)
        typer.echo(str(exc))


@app.command()
def write(
    text: Annotated[
        str | None,
        typer.Option("--text", "-t", help="블로그 글의 재료가 될 텍스트를 직접 붙여넣습니다."),
    ] = None,
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="재료가 들어 있는 텍스트 파일 경로."),
    ] = None,
    source_ref: Annotated[
        str | None,
        typer.Option("--source", "-s", help="출처로 남길 원문 링크 (선택)."),
    ] = None,
) -> None:
    """자료를 받아 블로그 글 초안을 작성한다.

    예) blog write --text "붙여넣은 자료..."
        blog write --file 자료.txt --source https://example.com/article
    """
    if text and file:
        _die("--text 와 --file 은 함께 쓸 수 없습니다. 하나만 고르세요.")

    if file:
        if not file.is_file():
            _die(f"파일을 찾을 수 없습니다: {file}")
        material = file.read_text(encoding="utf-8")
        kind, ref = "file", source_ref or str(file)
    elif text:
        material, kind, ref = text, "text", source_ref
    elif not sys.stdin.isatty():
        material, kind, ref = sys.stdin.read(), "text", source_ref
    else:
        _die(
            "재료가 없습니다.\n"
            '  예)  blog write --text "여기에 기사 내용을 붙여넣으세요"\n'
            "       blog write --file 자료.txt"
        )
        return

    material = material.strip()
    if not material:
        _die(
            "재료가 없습니다.\n"
            '  예)  blog write --text "여기에 기사 내용을 붙여넣으세요"\n'
            "       blog write --file 자료.txt"
        )
        return
    if len(material) < 100:
        _die(f"자료가 너무 짧습니다({len(material)}자). 최소 100자 이상 넣어 주세요.")

    try:
        config_module.api_key()
        settings = config_module.load()
    except config_module.ConfigError as exc:
        _die(str(exc))
        return

    def show(step: int, message: str) -> None:
        typer.secho(f"  [{step}/4] {message}...", fg=typer.colors.CYAN)

    typer.echo(f"\n글을 쓰기 시작합니다. (자료 {len(material)}자, 보통 1~2분 걸립니다)\n")
    try:
        source = Source(text=material, kind=kind, ref=ref)
        post, run_id, path = run_pipeline(source, settings, on_step=show)
    except LLMError as exc:
        _die(str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - 사용자에게 원문 그대로 보여 주는 편이 낫다
        _die(f"예상치 못한 오류가 생겼습니다: {exc}")
        return

    typer.echo("")
    typer.secho("[완료] 초안이 만들어졌습니다.", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"  제목    {post.title}")
    typer.echo(f"  태그    {', '.join(post.tags) if post.tags else '(없음)'}")
    typer.echo(f"  저장    {path}")
    typer.echo("")
    typer.secho("다른 제목 후보", fg=typer.colors.CYAN)
    for candidate in post.title_candidates[1:]:
        typer.echo(f"  - {candidate}")
    typer.echo("")
    typer.echo(f"  이력 번호 {run_id} · 예상 비용 약 ${post.usage.cost_usd:.3f}")
    typer.echo(f"  파일 열기:  open {settings.drafts_dir}")


@app.command(name="list")
def list_runs(
    limit: Annotated[int, typer.Option("--limit", "-n", help="몇 건까지 볼지.")] = 20,
) -> None:
    """지금까지 생성한 글 이력을 보여준다."""
    conn = db.connect()
    try:
        rows = db.recent(conn, limit=limit)
    finally:
        conn.close()

    if not rows:
        typer.echo("아직 만든 글이 없습니다.  blog write --text \"...\" 로 첫 글을 써 보세요.")
        return

    typer.secho(f"{'번호':<5}{'날짜':<21}{'상태':<11}제목", bold=True)
    for row in rows:
        title = row.title or (row.error or "")[:40] or "(제목 없음)"
        typer.echo(f"{row.id:<5}{row.created_at:<21}{row.status:<11}{title}")

    total = sum(row.cost_usd for row in rows)
    typer.echo(f"\n합계 예상 비용 약 ${total:.3f}")


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
