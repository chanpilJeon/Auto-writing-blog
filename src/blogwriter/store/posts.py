"""완성된 글을 frontmatter 붙은 마크다운 파일로 저장한다.

파일명: ``~/BlogDrafts/2026-09-04-제목-슬러그.md``
frontmatter를 쓰는 이유는 어떤 발행 경로(워드프레스·깃허브페이지·복붙)로든
그대로 변환할 수 있는 중립 포맷이기 때문이다.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import frontmatter

from blogwriter.core.models import Post

_SLUG_DROP = re.compile(r"[^0-9A-Za-z가-힣\s-]")
_SLUG_SPACE = re.compile(r"[\s_]+")


def slugify(title: str, *, max_length: int = 40) -> str:
    """제목을 파일명에 쓸 수 있는 형태로 바꾼다. 한글은 그대로 남긴다."""
    text = _SLUG_DROP.sub("", title).strip()
    text = _SLUG_SPACE.sub("-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return text[:max_length].strip("-") or "untitled"


def _unique(path: Path) -> Path:
    """같은 이름이 있으면 -2, -3 을 붙인다."""
    if not path.exists():
        return path
    for number in range(2, 100):
        candidate = path.with_name(f"{path.stem}-{number}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"파일 이름이 너무 많이 겹칩니다: {path}")


def save(post: Post, drafts_dir: Path) -> Path:
    """Post를 마크다운 파일로 저장하고 경로를 돌려준다."""
    drafts_dir = drafts_dir.expanduser()
    drafts_dir.mkdir(parents=True, exist_ok=True)

    document = frontmatter.Post(post.body)
    document["title"] = post.title
    document["date"] = post.created.isoformat()
    document["tags"] = post.tags
    document["description"] = post.description
    document["status"] = "draft"
    if post.source_ref:
        document["source"] = post.source_ref
    if post.title_candidates:
        document["title_candidates"] = post.title_candidates

    path = _unique(drafts_dir / f"{post.created.isoformat()}-{slugify(post.title)}.md")
    path.write_text(frontmatter.dumps(document) + "\n", encoding="utf-8")
    return path


def load(path: Path) -> Post:
    """저장된 마크다운 파일을 다시 Post로 읽어 들인다."""
    if not path.is_file():
        raise FileNotFoundError(f"글 파일을 찾을 수 없습니다: {path}")

    document = frontmatter.loads(path.read_text(encoding="utf-8"))
    raw_date = document.get("date")
    created = date.fromisoformat(str(raw_date)) if raw_date else date.today()

    return Post(
        title=str(document.get("title", path.stem)),
        body=document.content,
        tags=[str(tag) for tag in document.get("tags", []) or []],
        description=str(document.get("description", "") or ""),
        source_ref=document.get("source") or None,
        created=created,
        title_candidates=[str(t) for t in document.get("title_candidates", []) or []],
    )
