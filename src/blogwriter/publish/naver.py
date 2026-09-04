"""네이버 블로그(스마트에디터 ONE) 발행 어댑터.

네이버는 2020년 5월 글쓰기 API를 종료했고 티스토리도 2024년 2월 Open API를 닫았다.
브라우저 자동화는 약관 위반이라 쓰지 않는다. 그래서 이 어댑터가 하는 일은
**에디터에 그대로 붙여 넣을 수 있는 상태까지 준비**하는 것이다.
"""

from __future__ import annotations

from blogwriter.core.models import Post
from blogwriter.publish import clipboard, render
from blogwriter.publish.base import PublishResult


class NaverClipboardPublisher:
    """본문을 네이버용 HTML로 바꿔 클립보드에 넣는다."""

    name = "clipboard-naver"

    def __init__(self, *, plain_only: bool = False, with_source: bool = True) -> None:
        self.plain_only = plain_only
        self.with_source = with_source

    def publish(self, post: Post) -> PublishResult:
        source_ref = post.source_ref if self.with_source else None
        plain = render.to_plain_text(post.body, source_ref=source_ref)

        if self.plain_only:
            clipboard.copy_plain(plain)
            summary = "본문을 평문으로 클립보드에 복사했습니다."
            notes = [
                "서식(소제목·굵게·링크)은 빠집니다. "
                "서식을 살리려면 --format html 로 실행하세요."
            ]
        else:
            html = render.to_naver_html(post.body, source_ref=source_ref)
            clipboard.copy_rich(html, plain)
            summary = "본문을 서식 그대로 클립보드에 복사했습니다."
            notes = [
                "붙여넣기 후 '외부 콘텐츠를 붙여넣었습니다' 안내가 뜨면 그대로 두면 됩니다.",
                "서식이 깨져 보이면 --format text 로 다시 복사해 평문으로 붙여넣으세요.",
            ]

        steps = [
            "네이버 블로그 > 글쓰기 를 엽니다.",
            f"제목 칸에 붙여넣기:  {post.title}",
            "본문 칸을 클릭하고 ⌘+V 로 붙여넣습니다.",
        ]
        if post.tags:
            tags = ", ".join(tag.replace(" ", "") for tag in post.tags)
            steps.append(f"태그 칸에 하나씩 입력:  {tags}")
        steps.append("내용을 한 번 읽어 보고 발행 버튼을 누릅니다.")

        if not self.plain_only:
            notes.append(
                "네이버는 CSS 클래스를 지우므로 글자 크기·줄간격을 태그마다 직접 넣어 두었습니다."
            )

        return PublishResult(target=self.name, summary=summary, steps=steps, notes=notes)
