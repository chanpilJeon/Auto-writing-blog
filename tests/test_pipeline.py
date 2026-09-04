"""파이프라인 전체 흐름 테스트 (Claude 호출은 전부 가짜)."""

from __future__ import annotations

import frontmatter

from blogwriter.core.models import Source
from blogwriter.core.pipeline import run
from blogwriter.store import db

SOURCE_TEXT = "자료 원문이다. " * 20


def test_run_produces_post_and_file(fake_backend, isolated_config):
    post, run_id, path = run(
        Source(text=SOURCE_TEXT, kind="text", ref="https://example.com/a"),
        isolated_config,
        backend=fake_backend,
    )

    # 첫 번째 제목 후보가 최종 제목이 된다
    assert post.title == "첫 번째 제목"
    assert post.tags == ["블로그", "자동화", "CLI"]
    assert "## 무엇이 달라졌나" in post.body
    assert post.usage.input_tokens == 3000  # 3단계 × 1000
    assert post.usage.cost_usd > 0

    # 파일이 frontmatter와 함께 저장된다
    assert path.exists()
    saved = frontmatter.loads(path.read_text(encoding="utf-8"))
    assert saved["title"] == "첫 번째 제목"
    assert saved["status"] == "draft"
    assert saved["source"] == "https://example.com/a"
    assert saved["tags"] == ["블로그", "자동화", "CLI"]

    # 이력이 SQLite에 남는다
    conn = db.connect()
    try:
        row = db.get(conn, run_id)
        assert row["status"] == "polished"
        assert row["title"] == "첫 번째 제목"
        assert row["post_path"] == str(path)
        assert row["plan_json"] is not None
        assert row["draft_md"] is not None
    finally:
        conn.close()


def test_three_claude_calls_in_order(fake_backend, isolated_config):
    run(Source(text=SOURCE_TEXT), isolated_config, backend=fake_backend)

    calls = fake_backend.calls
    assert len(calls) == 3
    # 1) 기획: 자료가 프롬프트에 들어간다
    assert SOURCE_TEXT.strip()[:20] in calls[0]["prompt"]
    # 2) 작성: 기획안의 소제목이 프롬프트에 들어간다
    assert "무엇이 달라졌나" in calls[1]["prompt"]
    # 3) 다듬기: 완성된 본문이 프롬프트에 들어간다
    assert "또 본문이다" in calls[2]["prompt"]


def test_failure_is_recorded(isolated_config, make_backend_with):
    broken = make_backend_with(["JSON이 아닌 응답"])
    try:
        run(Source(text=SOURCE_TEXT), isolated_config, backend=broken)
    except Exception:
        pass
    else:
        raise AssertionError("실패해야 하는데 성공했습니다.")

    conn = db.connect()
    try:
        assert db.recent(conn)[0].status == "failed"
    finally:
        conn.close()


def test_local_file_path_is_not_leaked_as_source(fake_backend, isolated_config):
    """--file 로 넣은 로컬 경로가 블로그에 출처로 노출되면 안 된다."""
    post, _, path = run(
        Source(text=SOURCE_TEXT, kind="file", ref="자료/기사.txt"),
        isolated_config,
        backend=fake_backend,
    )
    assert post.source_ref is None
    assert "자료/기사.txt" not in path.read_text(encoding="utf-8")
