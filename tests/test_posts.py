"""마크다운 저장·슬러그 테스트."""

from __future__ import annotations

from datetime import date

from blogwriter.core.models import Post
from blogwriter.store.posts import save, slugify


def test_slugify_keeps_hangul():
    assert slugify("블로그 자동 작성 도구") == "블로그-자동-작성-도구"
    assert slugify("Claude API: 비용 정리!") == "Claude-API-비용-정리"
    assert slugify("!!!") == "untitled"
    assert len(slugify("가" * 100)) <= 40


def test_save_writes_dated_filename(tmp_path):
    post = Post(title="테스트 제목", body="본문", created=date(2026, 9, 4))
    path = save(post, tmp_path)
    assert path.name == "2026-09-04-테스트-제목.md"


def test_save_avoids_overwriting(tmp_path):
    post = Post(title="같은 제목", body="본문", created=date(2026, 9, 4))
    first = save(post, tmp_path)
    second = save(post, tmp_path)
    assert first != second
    assert second.name.endswith("-2.md")
