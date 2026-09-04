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
from blogwriter.core.backends import ClaudeCodeBackend
from blogwriter.core.llm import LLMError
from blogwriter.core.models import Source
from blogwriter.core.pipeline import run as run_pipeline
from blogwriter.publish.base import PublishResult
from blogwriter.publish.clipboard import ClipboardError
from blogwriter.publish.naver import NaverClipboardPublisher
from blogwriter.store import db, posts

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

    typer.secho("Claude 연결 방식", fg=typer.colors.CYAN, bold=True)
    if settings.backend == "claude-code":
        typer.echo("  claude-code — 이미 쓰는 Claude 구독으로 돌립니다 (API 키 불필요)")
        cli_path = ClaudeCodeBackend.find_cli()
        if cli_path:
            typer.secho(f"  준비됨: {cli_path}", fg=typer.colors.GREEN)
        else:
            typer.secho("  claude 명령을 찾을 수 없습니다.", fg=typer.colors.RED)
            typer.echo("  터미널에서 `claude --version` 이 되는지 확인하세요.")
    else:
        typer.echo("  api — Claude API를 직접 호출합니다 (ANTHROPIC_API_KEY 필요)")
        try:
            key = config_module.api_key()
            typer.secho(f"  준비됨: {key[:10]}...", fg=typer.colors.GREEN)
        except config_module.ConfigError as exc:
            typer.secho("  API 키 없음", fg=typer.colors.RED)
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
        settings = config_module.load()
        if settings.backend == "api":
            config_module.api_key()
    except config_module.ConfigError as exc:
        _die(str(exc))
        return

    def show(step: int, message: str) -> None:
        typer.secho(f"  [{step}/4] {message}...", fg=typer.colors.CYAN)

    how = "Claude Code 구독" if settings.backend == "claude-code" else "Claude API"
    typer.echo(f"\n글을 쓰기 시작합니다. ({how} 사용 · 자료 {len(material)}자 · 보통 2~4분)\n")
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
    if settings.backend == "claude-code":
        typer.echo(
            f"  이력 번호 {run_id} · 사용량 환산 약 ${post.usage.cost_usd:.3f} "
            "(구독으로 돌렸으므로 추가 청구는 없습니다)"
        )
    else:
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


def _resolve_post_row(conn, run_id: int | None):
    """발행할 글의 이력 행을 찾는다. 번호를 안 주면 가장 최근 글."""
    if run_id is not None:
        row = db.get(conn, run_id)
        if row is None:
            _die(f"{run_id}번 글이 없습니다.  blog list 로 번호를 확인하세요.")
        if not row["post_path"]:
            _die(f"{run_id}번은 글 파일이 없습니다(상태: {row['status']}).")
        return row

    row = db.latest_with_post(conn)
    if row is None:
        _die('아직 발행할 글이 없습니다.  blog write --text "..." 로 먼저 글을 써 보세요.')
    return row


def _show_result(result: PublishResult) -> None:
    typer.secho(f"[완료] {result.summary}", fg=typer.colors.GREEN, bold=True)
    typer.echo("")
    typer.secho("이제 이렇게 하세요", fg=typer.colors.CYAN, bold=True)
    for number, step in enumerate(result.steps, start=1):
        typer.echo(f"  {number}. {step}")
    if result.notes:
        typer.echo("")
        for note in result.notes:
            typer.echo(f"  · {note}")


@app.command()
def publish(
    run_id: Annotated[
        int | None,
        typer.Argument(help="발행할 글 번호. 생략하면 가장 최근 글."),
    ] = None,
    fmt: Annotated[
        str,
        typer.Option("--format", help="html(서식 유지, 기본) 또는 text(평문)."),
    ] = "html",
    with_source: Annotated[
        bool,
        typer.Option("--source/--no-source", help="글 끝에 출처 링크를 붙일지."),
    ] = True,
) -> None:
    """완성된 글을 네이버 블로그에 붙여 넣을 수 있게 클립보드로 복사한다.

    네이버·티스토리는 글쓰기 API가 종료돼 자동 발행이 불가능하다.
    그래서 '붙여넣기 직전'까지를 자동화한다.
    """
    if fmt not in {"html", "text"}:
        _die("--format 은 html 또는 text 만 됩니다.")

    conn = db.connect()
    try:
        row = _resolve_post_row(conn, run_id)
        path = Path(row["post_path"])
        try:
            post = posts.load(path)
        except FileNotFoundError as exc:
            _die(f"{exc}\n  파일을 옮기거나 지우지 않았는지 확인하세요.")
            return

        publisher = NaverClipboardPublisher(
            plain_only=(fmt == "text"), with_source=with_source
        )
        try:
            result = publisher.publish(post)
        except ClipboardError as exc:
            _die(str(exc))
            return

        db.update(conn, row["id"], status="published", published_to=result.target)
    finally:
        conn.close()

    typer.echo("")
    _show_result(result)


if __name__ == "__main__":
    app()
