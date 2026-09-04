"""파이프라인 전체를 순서대로 돌리는 오케스트레이터.

CLI를 전혀 모른다. 진행 상황은 ``on_step`` 콜백으로만 밖에 알린다.
나중에 웹 UI나 에이전트가 붙어도 이 파일은 그대로 재사용한다.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from blogwriter.config import Config
from blogwriter.core import planner, polisher, writer
from blogwriter.core.backends import ApiBackend, Backend, ClaudeCodeBackend
from blogwriter.core.models import Plan, Post, Source, Usage
from blogwriter.store import db, posts

# (단계 번호, 사람이 읽는 설명)을 받는 콜백
StepCallback = Callable[[int, str], None]


def _noop(step: int, message: str) -> None:  # pragma: no cover - 기본 콜백
    pass


def _is_public_url(ref: str | None) -> bool:
    """블로그에 노출해도 되는 주소인지."""
    return bool(ref) and ref.startswith(("http://", "https://"))


def make_backend(config: Config) -> Backend:
    """설정에 적힌 경로(claude-code / api)로 백엔드를 만든다."""
    if config.backend == "api":
        return ApiBackend()
    return ClaudeCodeBackend(config.claude_workdir)


def run(
    source: Source,
    config: Config,
    *,
    backend: Backend | None = None,
    on_step: StepCallback = _noop,
) -> tuple[Post, int, Path]:
    """자료 → 기획 → 작성 → 다듬기 → 파일 저장.

    Returns:
        (완성된 Post, SQLite 실행 id, 저장된 마크다운 파일 경로)
    """
    backend = backend or make_backend(config)
    style_guide = config.style_guide
    usage = Usage()

    conn = db.connect()
    run_id = db.start_run(conn, source_type=source.kind, source_ref=source.ref)

    def record(step_usage: Usage) -> None:
        usage.add(step_usage)
        db.add_usage(
            conn, run_id, step_usage.input_tokens, step_usage.output_tokens, step_usage.cost_usd
        )

    try:
        on_step(1, "자료를 읽고 글의 각도와 목차를 잡는 중")
        plan, step_usage = planner.make_plan(
            backend, source, model=config.plan_model, style_guide=style_guide
        )
        record(step_usage)
        db.update(conn, run_id, status="planned", plan_json=plan.to_dict())

        on_step(2, "본문을 쓰는 중 (가장 오래 걸립니다)")
        draft, step_usage = writer.write_draft(
            backend, source, plan, model=config.write_model, style_guide=style_guide
        )
        record(step_usage)
        db.update(conn, run_id, status="drafted", draft_md=draft.body)

        on_step(3, "제목 후보와 태그를 뽑는 중")
        polished, step_usage = polisher.polish(
            backend, draft, model=config.polish_model, style_guide=style_guide
        )
        record(step_usage)

        title = polished.titles[0] if polished.titles else plan.working_title or "제목 없음"
        # 출처로 내보내는 것은 공개 URL뿐이다.
        # --file 로 넣은 로컬 경로가 블로그에 노출되면 곤란하다.
        public_ref = source.ref if _is_public_url(source.ref) else None
        post = Post(
            title=title,
            body=draft.body,
            tags=polished.tags,
            description=polished.description,
            source_ref=public_ref,
            title_candidates=polished.titles,
            usage=usage,
        )

        on_step(4, "파일로 저장하는 중")
        path = posts.save(post, config.drafts_dir)
        db.update(conn, run_id, status="polished", title=title, post_path=str(path))
        return post, run_id, path
    except Exception as exc:
        db.update(conn, run_id, status="failed", error=str(exc))
        raise
    finally:
        conn.close()


def plan_only(
    source: Source,
    config: Config,
    *,
    backend: Backend | None = None,
    on_step: StepCallback = _noop,
) -> tuple[Plan, int]:
    """기획안까지만 만든다 (``blog plan`` 용, Phase 2에서 CLI에 연결)."""
    backend = backend or make_backend(config)
    conn = db.connect()
    run_id = db.start_run(conn, source_type=source.kind, source_ref=source.ref)
    try:
        on_step(1, "자료를 읽고 글의 각도와 목차를 잡는 중")
        plan, step_usage = planner.make_plan(
            backend, source, model=config.plan_model, style_guide=config.style_guide
        )
        db.add_usage(
            conn, run_id, step_usage.input_tokens, step_usage.output_tokens, step_usage.cost_usd
        )
        db.update(conn, run_id, status="planned", plan_json=plan.to_dict())
        return plan, run_id
    except Exception as exc:
        db.update(conn, run_id, status="failed", error=str(exc))
        raise
    finally:
        conn.close()
