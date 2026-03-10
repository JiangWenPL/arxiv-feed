"""SQLite database schema and operations for arxiv-feed."""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

DB_PATH = Path(__file__).parent.parent.parent / "data" / "feed.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,            -- 'arxiv', 'blog', 'twitter'
    source_id TEXT UNIQUE,           -- arxiv ID, URL, or tweet ID
    title TEXT NOT NULL,
    authors TEXT NOT NULL,            -- comma-separated
    abstract TEXT,
    url TEXT NOT NULL,
    category TEXT NOT NULL,           -- 'latest_research', 'ml_infra', 'learning_methods', 'general_reading'
    subcategory TEXT,                 -- e.g. '3dgs', 'flash_attention', 'quant_math'
    tags TEXT,                        -- comma-separated keywords
    score REAL DEFAULT 0.0,           -- relevance score from scorer
    date_published TEXT,
    date_added TEXT NOT NULL,
    date_updated TEXT
);

CREATE TABLE IF NOT EXISTS reading_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER UNIQUE NOT NULL REFERENCES papers(id),
    status TEXT NOT NULL DEFAULT 'unread',  -- 'unread', 'reading', 'done'
    notes TEXT,
    archived_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS authors_whitelist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    affiliation TEXT,
    source_handle TEXT,              -- twitter handle, blog URL
    credibility_tier INTEGER DEFAULT 2,  -- 1=top, 2=solid, 3=emerging
    topics TEXT                       -- comma-separated
);

CREATE INDEX IF NOT EXISTS idx_papers_category ON papers(category);
CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(date_added);
CREATE INDEX IF NOT EXISTS idx_papers_score ON papers(score DESC);
CREATE INDEX IF NOT EXISTS idx_reading_status ON reading_status(status);
"""


def get_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    conn = get_db(db_path)
    conn.executescript(SCHEMA)
    conn.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_paper(
    conn: sqlite3.Connection,
    source: str,
    source_id: str,
    title: str,
    authors: str,
    url: str,
    category: str,
    abstract: str = "",
    subcategory: str = "",
    tags: str = "",
    score: float = 0.0,
    date_published: str = "",
) -> Optional[int]:
    """Insert a paper, skip if source_id already exists. Returns row id or None."""
    try:
        cur = conn.execute(
            """INSERT INTO papers
               (source, source_id, title, authors, abstract, url, category,
                subcategory, tags, score, date_published, date_added)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (source, source_id, title, authors, abstract, url, category,
             subcategory, tags, score, date_published, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_papers(
    conn: sqlite3.Connection,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Fetch papers, optionally filtered by category and reading status."""
    query = "SELECT p.*, rs.status, rs.notes, rs.archived_at FROM papers p"
    query += " LEFT JOIN reading_status rs ON p.id = rs.paper_id"
    conditions = []
    params = []
    if category:
        conditions.append("p.category = ?")
        params.append(category)
    if status:
        if status == "unread":
            conditions.append("(rs.status IS NULL OR rs.status = 'unread')")
        else:
            conditions.append("rs.status = ?")
            params.append(status)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY p.score DESC, p.date_added DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def update_reading_status(
    conn: sqlite3.Connection,
    paper_id: int,
    status: str,
    notes: Optional[str] = None,
) -> None:
    archived_at = now_iso() if status == "done" else None
    conn.execute(
        """INSERT INTO reading_status (paper_id, status, notes, archived_at, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(paper_id) DO UPDATE SET
             status=excluded.status,
             notes=COALESCE(excluded.notes, reading_status.notes),
             archived_at=COALESCE(excluded.archived_at, reading_status.archived_at),
             updated_at=excluded.updated_at""",
        (paper_id, status, notes, archived_at, now_iso()),
    )
    conn.commit()


def get_digest(conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    """Get top unread papers for the daily digest."""
    return [dict(row) for row in conn.execute(
        """SELECT p.*, rs.status FROM papers p
           LEFT JOIN reading_status rs ON p.id = rs.paper_id
           WHERE rs.status IS NULL OR rs.status = 'unread'
           ORDER BY p.score DESC, p.date_added DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()]
