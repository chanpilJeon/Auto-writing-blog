"""네이버 발행(클립보드) 어댑터 테스트."""

from __future__ import annotations

from datetime import date

import pytest

from blogwriter.core.models import Post
from blogwriter.publish import clipboard, render
from blogwriter.publish.naver import NaverClipboardPublisher

BODY = """## 무엇이 달라졌나

첫 문단이다. **굵은 글씨**와 [링크](https://example.com)가 들어 있다.

- 첫째 항목
- 둘째 항목

> 인용문이다.
"""


@pytest.fixture
def captured(monkeypatch):
    """클립보드에 실제로 쓰지 않고 내용만 가로챈다."""
    box: dict[str, str] = {}
    monkeypatch.setattr(
        clipboard, "copy_rich", lambda html, plain: box.update(html=html, plain=plain)
    )
    monkeypatch.setattr(clipboard, "copy_plain", lambda text: box.update(plain=text))
    return box


def test_naver_html_has_inline_styles():
    html = render.to_naver_html(BODY)
    # 네이버는 CSS 클래스를 버리므로 태그마다 style이 박혀 있어야 한다
    assert '<h2 style="font-size:19px' in html
    assert '<p style="font-size:15px' in html
    assert '<li style=' in html
    assert '<blockquote style=' in html
    # 링크와 강조는 그대로 살아 있어야 한다
    assert '<a href="https://example.com">링크</a>' in html
    assert "<strong>굵은 글씨</strong>" in html


def test_existing_style_attribute_is_not_overwritten():
    html = render.inline_styles('<p style="color:red">x</p>', render.NAVER_STYLES)
    assert html == '<p style="color:red">x</p>'


def test_source_footer_added_only_when_source_exists():
    assert "출처" in render.to_naver_html(BODY, source_ref="https://example.com/a")
    assert "출처" not in render.to_naver_html(BODY)


def test_plain_text_strips_markdown_symbols():
    text = render.to_plain_text(BODY)
    assert "##" not in text
    assert "**" not in text
    assert "무엇이 달라졌나" in text
    assert "링크(https://example.com)" in text
    assert "· 첫째 항목" in text


def test_publish_copies_rich_and_returns_steps(captured):
    post = Post(
        title="테스트 제목",
        body=BODY,
        tags=["태그A", "태그B"],
        source_ref="https://example.com/a",
        created=date(2026, 9, 4),
    )
    result = NaverClipboardPublisher().publish(post)

    assert result.target == "clipboard-naver"
    assert "style=" in captured["html"]
    assert "출처" in captured["html"]
    # 제목은 본문 HTML에 들어가면 안 된다 (네이버는 제목 칸이 따로 있다)
    assert "테스트 제목" not in captured["html"]
    # 안내에는 제목과 태그가 그대로 나와야 한다
    assert any("테스트 제목" in step for step in result.steps)
    assert any("태그A, 태그B" in step for step in result.steps)


def test_publish_text_format_copies_plain_only(captured):
    post = Post(title="제목", body=BODY)
    NaverClipboardPublisher(plain_only=True).publish(post)
    assert "html" not in captured
    assert "##" not in captured["plain"]


def test_tag_spaces_are_removed(captured):
    """네이버 태그 입력창은 공백에서 잘리므로 공백을 없애고 안내한다."""
    post = Post(title="제목", body=BODY, tags=["오픈소스 AI", "AI 스택"])
    result = NaverClipboardPublisher().publish(post)
    assert any("오픈소스AI, AI스택" in step for step in result.steps)


def test_no_source_option(captured):
    post = Post(title="제목", body=BODY, source_ref="https://example.com/a")
    NaverClipboardPublisher(with_source=False).publish(post)
    assert "출처" not in captured["html"]
