"""마크다운을 블로그 에디터가 잘 받아먹는 HTML로 바꾼다.

네이버 스마트에디터는 CSS 클래스나 <style> 태그를 버리고 **인라인 style만** 남긴다.
그래서 서식을 지키려면 태그마다 style 속성을 직접 박아 넣어야 한다.
"""

from __future__ import annotations

import re

import markdown

# 태그 → 붙여 넣을 인라인 스타일. 네이버 본문 기본값(15px, 줄간격 1.8)에 맞춘 값.
NAVER_STYLES: dict[str, str] = {
    "h1": "font-size:22px;font-weight:700;margin:36px 0 14px;line-height:1.5",
    "h2": "font-size:19px;font-weight:700;margin:32px 0 12px;line-height:1.5",
    "h3": "font-size:17px;font-weight:700;margin:26px 0 10px;line-height:1.5",
    "p": "font-size:15px;line-height:1.8;margin:0 0 16px",
    "li": "font-size:15px;line-height:1.8;margin:0 0 6px",
    "ul": "margin:0 0 16px;padding-left:22px",
    "ol": "margin:0 0 16px;padding-left:22px",
    "blockquote": (
        "margin:20px 0;padding:10px 0 10px 16px;border-left:3px solid #d0d0d0;color:#555"
    ),
    "pre": (
        "font-family:Menlo,Consolas,monospace;font-size:13px;line-height:1.6;"
        "background:#f5f5f5;padding:14px;border-radius:4px;overflow-x:auto"
    ),
    "code": "font-family:Menlo,Consolas,monospace;font-size:13px",
    "table": "border-collapse:collapse;margin:0 0 16px",
    "th": "border:1px solid #ddd;padding:6px 10px;background:#fafafa;font-size:14px",
    "td": "border:1px solid #ddd;padding:6px 10px;font-size:14px",
}


def markdown_to_html(body: str) -> str:
    """마크다운 → 순수 HTML (스타일 없음)."""
    return markdown.markdown(body, extensions=["extra", "sane_lists", "nl2br"])


def inline_styles(html: str, styles: dict[str, str]) -> str:
    """여는 태그에 style 속성을 넣는다. 이미 style이 있으면 건드리지 않는다."""

    def add_style(match: re.Match[str]) -> str:
        tag, attrs = match.group(1), match.group(2)
        style = styles.get(tag.lower())
        if not style or "style=" in attrs:
            return match.group(0)
        return f"<{tag}{attrs} style=\"{style}\">"

    return re.sub(r"<([a-zA-Z][a-zA-Z0-9]*)((?:\s[^<>]*)?)>", add_style, html)


def source_footer(source_ref: str | None) -> str:
    """글 끝에 붙일 출처 표기. 원문을 재서술했더라도 출처는 남기는 게 원칙이다."""
    if not source_ref:
        return ""
    # 본문 문단 스타일에서 글자 크기만 갈아 끼운다 (중복 font-size 방지)
    base = ";".join(
        rule for rule in NAVER_STYLES["p"].split(";") if not rule.startswith("font-size")
    )
    style = f"font-size:13px;{base};color:#888"
    return f'<p style="{style}">출처: <a href="{source_ref}">{source_ref}</a></p>'


def to_naver_html(body: str, *, source_ref: str | None = None) -> str:
    """네이버 스마트에디터에 붙여 넣을 HTML."""
    html = inline_styles(markdown_to_html(body), NAVER_STYLES)
    footer = source_footer(source_ref)
    return f"{html}\n{footer}" if footer else html


def to_plain_text(body: str, *, source_ref: str | None = None) -> str:
    """서식 붙여넣기가 막혔을 때 쓸 평문. 마크다운 기호만 걷어낸다."""
    text = re.sub(r"^#{1,6}\s*", "", body, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1(\2)", text)
    text = re.sub(r"^\s*[-*]\s+", "· ", text, flags=re.MULTILINE)
    text = text.strip()
    if source_ref:
        text += f"\n\n출처: {source_ref}"
    return text
