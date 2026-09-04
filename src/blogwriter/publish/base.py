"""발행 어댑터가 지켜야 할 인터페이스.

발행 방식(클립보드·워드프레스·깃허브페이지)이 늘어나도 CLI는 이 인터페이스만 안다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from blogwriter.core.models import Post


@dataclass
class PublishResult:
    """발행 결과와 사용자에게 보여 줄 다음 행동 안내."""

    target: str  # 이력에 남길 이름 (clipboard-naver 등)
    summary: str  # 한 줄 결과 요약
    steps: list[str] = field(default_factory=list)  # 사람이 이어서 할 일
    notes: list[str] = field(default_factory=list)  # 참고 사항


class Publisher(Protocol):
    """발행 어댑터."""

    name: str

    def publish(self, post: Post) -> PublishResult:
        """글을 발행(또는 발행 직전 상태로 준비)한다."""
        ...
