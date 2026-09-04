"""처리 이력을 담는 SQLite 저장소.

파일 하나(``~/.local/share/blogwriter/blogwriter.db``)만 쓴다. 서버도 설치도 필요 없다.
단계별 산출물을 저장해 두므로 나중에 ``blog resume``으로 중간부터 다시 돌릴 수 있다.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from blogwriter import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_ref TEXT,
  status TEXT NOT NULL,
  plan_json TEXT,
  draft_md TEXT,
  title TEXT,
  post_path TEXT,
  published_to TEXT,
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  cost_usd REAL DEFAULT 0,
  error TEXT
);
"""


@dataclass
class Run:
    """이력 한 줄."""

    id: int
    created_at: str
    source_type: str
    source_ref: str | None
    status: str
    title: str | None
    post_path: str | None
    cost_usd: float
    error: str | None


def db_path() -> Path:
    return config.DATA_DIR / "blogwriter.db"


def connect() -> sqlite3.Connection:
    """DB 파일을 열고 스키마를 보장한다."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def start_run(conn: sqlite3.Connection, *, source_type: str, source_ref: str | None) -> int:
    """새 실행을 기록하고 id를 돌려준다."""
    cursor = conn.execute(
        "INSERT INTO runs (created_at, source_type, source_ref, status) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), source_type, source_ref, "started"),
    )
    conn.commit()
    return int(cursor.lastrowid)


def update(conn: sqlite3.Connection, run_id: int, **fields: object) -> None:
    """실행 기록의 일부 칼럼을 갱신한다. dict/list 값은 JSON으로 저장한다."""
    if not fields:
        return
    columns, values = [], []
    for key, value in fields.items():
        columns.append(f"{key} = ?")
        if isinstance(value, dict | list):
            value = json.dumps(value, ensure_ascii=False)
        values.append(value)
    values.append(run_id)
    conn.execute(f"UPDATE runs SET {', '.join(columns)} WHERE id = ?", values)
    conn.commit()


def add_usage(
    conn: sqlite3.Connection, run_id: int, tokens_in: int, tokens_out: int, cost: float
) -> None:
    """토큰·비용을 누적한다."""
    conn.execute(
        "UPDATE runs SET tokens_in = tokens_in + ?, tokens_out = tokens_out + ?, "
        "cost_usd = cost_usd + ? WHERE id = ?",
        (tokens_in, tokens_out, cost, run_id),
    )
    conn.commit()


def _to_run(row: sqlite3.Row) -> Run:
    return Run(
        id=row["id"],
        created_at=row["created_at"],
        source_type=row["source_type"],
        source_ref=row["source_ref"],
        status=row["status"],
        title=row["title"],
        post_path=row["post_path"],
        cost_usd=row["cost_usd"] or 0.0,
        error=row["error"],
    )


def recent(conn: sqlite3.Connection, limit: int = 20) -> list[Run]:
    """최근 실행 이력."""
    rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_to_run(row) for row in rows]


def get(conn: sqlite3.Connection, run_id: int) -> sqlite3.Row | None:
    """실행 한 건 전체(기획안·초안 포함)."""
    return conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()


def latest_with_post(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """글 파일이 만들어진 것 중 가장 최근 실행."""
    return conn.execute(
        "SELECT * FROM runs WHERE post_path IS NOT NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
