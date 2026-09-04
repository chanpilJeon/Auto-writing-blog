"""파이프라인 단계 사이를 오가는 데이터 구조.

CLI·저장소·API를 전혀 모르는 순수 데이터클래스만 둔다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass
class Source:
    """① 수집·정제 단계의 산출물 — 글의 재료."""

    text: str
    kind: str = "text"  # text | url | file | notion
    ref: str | None = None  # 원본 URL 또는 파일 경로
    title: str | None = None  # 원문 제목(알 수 있으면)


@dataclass
class Section:
    """기획안의 소제목 하나."""

    heading: str
    points: list[str] = field(default_factory=list)


@dataclass
class Plan:
    """② 분석·구조화 단계의 산출물 — 무엇을 어떤 각도로 쓸지."""

    working_title: str
    angle: str
    target_reader: str
    sections: list[Section] = field(default_factory=list)
    key_facts: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Plan:
        return cls(
            working_title=str(data.get("working_title", "")).strip(),
            angle=str(data.get("angle", "")).strip(),
            target_reader=str(data.get("target_reader", "")).strip(),
            sections=[
                Section(
                    heading=str(s.get("heading", "")).strip(),
                    points=[str(p) for p in s.get("points", [])],
                )
                for s in data.get("sections", [])
            ],
            key_facts=[str(k) for k in data.get("key_facts", [])],
            cautions=[str(c) for c in data.get("cautions", [])],
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Draft:
    """③ 초안 작성 단계의 산출물 — 본문 마크다운."""

    body: str


@dataclass
class Polish:
    """④ 다듬기 단계의 산출물 — 제목 후보·태그·요약."""

    titles: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> Polish:
        return cls(
            titles=[str(t).strip() for t in data.get("titles", []) if str(t).strip()],
            tags=[str(t).strip() for t in data.get("tags", []) if str(t).strip()],
            description=str(data.get("description", "")).strip(),
        )


@dataclass
class Usage:
    """토큰 사용량·비용 누적치."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, other: Usage) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cost_usd += other.cost_usd


@dataclass
class Post:
    """⑤ 최종 결과물 — 저장·발행할 수 있는 완성 글."""

    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    description: str = ""
    source_ref: str | None = None
    created: date = field(default_factory=date.today)
    title_candidates: list[str] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
