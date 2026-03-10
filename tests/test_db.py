"""Tests for SQLite database operations."""

import pytest
from src.db.models import get_db, init_db, add_paper, get_papers, update_reading_status, get_digest


@pytest.fixture
def db(tmp_path):
    """Create a fresh in-memory-like test DB."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = get_db(db_path)
    yield conn
    conn.close()


def _insert_paper(conn, **overrides):
    defaults = {
        "source": "arxiv",
        "source_id": "2403.00001",
        "title": "Test Paper",
        "authors": "Author A, Author B",
        "url": "https://arxiv.org/abs/2403.00001",
        "category": "latest_research",
        "score": 10.0,
    }
    defaults.update(overrides)
    return add_paper(conn, **defaults)


class TestInitDb:
    def test_creates_tables(self, db):
        tables = [
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "papers" in tables
        assert "reading_status" in tables
        assert "authors_whitelist" in tables


class TestAddPaper:
    def test_insert_returns_id(self, db):
        row_id = _insert_paper(db)
        assert row_id is not None
        assert row_id > 0

    def test_duplicate_source_id_returns_none(self, db):
        _insert_paper(db, source_id="dup-1")
        result = _insert_paper(db, source_id="dup-1")
        assert result is None

    def test_different_source_ids_both_inserted(self, db):
        id1 = _insert_paper(db, source_id="a")
        id2 = _insert_paper(db, source_id="b")
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2


class TestGetPapers:
    def test_returns_all_papers(self, db):
        _insert_paper(db, source_id="1")
        _insert_paper(db, source_id="2")
        papers = get_papers(db)
        assert len(papers) == 2

    def test_filter_by_category(self, db):
        _insert_paper(db, source_id="1", category="latest_research")
        _insert_paper(db, source_id="2", category="ml_infra")
        papers = get_papers(db, category="latest_research")
        assert len(papers) == 1
        assert papers[0]["category"] == "latest_research"

    def test_ordered_by_score_desc(self, db):
        _insert_paper(db, source_id="low", score=1.0)
        _insert_paper(db, source_id="high", score=20.0)
        _insert_paper(db, source_id="mid", score=10.0)
        papers = get_papers(db)
        scores = [p["score"] for p in papers]
        assert scores == [20.0, 10.0, 1.0]

    def test_limit_and_offset(self, db):
        for i in range(5):
            _insert_paper(db, source_id=str(i), score=float(i))
        papers = get_papers(db, limit=2, offset=0)
        assert len(papers) == 2

    def test_filter_unread(self, db):
        _insert_paper(db, source_id="1")
        id2 = _insert_paper(db, source_id="2")
        update_reading_status(db, id2, "done")
        papers = get_papers(db, status="unread")
        assert len(papers) == 1
        assert papers[0]["source_id"] == "1"


class TestReadingStatus:
    def test_mark_reading(self, db):
        pid = _insert_paper(db)
        update_reading_status(db, pid, "reading")
        papers = get_papers(db, status="reading")
        assert len(papers) == 1

    def test_mark_done_sets_archived(self, db):
        pid = _insert_paper(db)
        update_reading_status(db, pid, "done")
        row = db.execute(
            "SELECT archived_at FROM reading_status WHERE paper_id = ?", (pid,)
        ).fetchone()
        assert row["archived_at"] is not None

    def test_update_notes(self, db):
        pid = _insert_paper(db)
        update_reading_status(db, pid, "reading", notes="Great paper")
        row = db.execute(
            "SELECT notes FROM reading_status WHERE paper_id = ?", (pid,)
        ).fetchone()
        assert row["notes"] == "Great paper"

    def test_upsert_keeps_existing_notes(self, db):
        pid = _insert_paper(db)
        update_reading_status(db, pid, "reading", notes="First note")
        update_reading_status(db, pid, "done")  # no notes param
        row = db.execute(
            "SELECT notes FROM reading_status WHERE paper_id = ?", (pid,)
        ).fetchone()
        assert row["notes"] == "First note"


class TestGetDigest:
    def test_returns_top_unread(self, db):
        _insert_paper(db, source_id="1", score=20.0)
        _insert_paper(db, source_id="2", score=5.0)
        pid3 = _insert_paper(db, source_id="3", score=30.0)
        update_reading_status(db, pid3, "done")  # should be excluded
        digest = get_digest(db, limit=10)
        assert len(digest) == 2
        assert digest[0]["score"] == 20.0  # highest unread first

    def test_respects_limit(self, db):
        for i in range(10):
            _insert_paper(db, source_id=str(i))
        digest = get_digest(db, limit=3)
        assert len(digest) == 3
