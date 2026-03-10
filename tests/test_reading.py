"""Tests for the reading status CLI."""


import pytest
from src.db.models import get_db, init_db, add_paper, update_reading_status, get_papers


@pytest.fixture
def db_with_papers(tmp_path, monkeypatch):
    """Create a test DB with papers and patch DB_PATH."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = get_db(db_path)
    for i in range(5):
        add_paper(
            conn,
            source="arxiv",
            source_id=f"2403.{i:05d}",
            title=f"Test Paper {i}",
            authors=f"Author {i}",
            url=f"https://arxiv.org/abs/2403.{i:05d}",
            category="latest_research",
            score=float(20 - i),
        )
    conn.close()
    monkeypatch.setattr("src.db.models.DB_PATH", db_path)
    return db_path


class TestReadingCLI:
    def test_list_default(self, db_with_papers):
        """All papers start as unread."""
        conn = get_db(db_with_papers)
        papers = get_papers(conn, status="unread")
        conn.close()
        assert len(papers) == 5

    def test_mark_and_list(self, db_with_papers):
        conn = get_db(db_with_papers)
        papers = get_papers(conn)
        pid = papers[0]["id"]
        update_reading_status(conn, pid, "reading")

        reading = get_papers(conn, status="reading")
        assert len(reading) == 1
        assert reading[0]["id"] == pid

        unread = get_papers(conn, status="unread")
        assert len(unread) == 4
        conn.close()

    def test_mark_done_and_archive(self, db_with_papers):
        conn = get_db(db_with_papers)
        papers = get_papers(conn)
        pid = papers[0]["id"]
        update_reading_status(conn, pid, "done")

        done = get_papers(conn, status="done")
        assert len(done) == 1

        # Check archived_at is set
        row = conn.execute(
            "SELECT archived_at FROM reading_status WHERE paper_id = ?", (pid,)
        ).fetchone()
        assert row["archived_at"] is not None
        conn.close()

    def test_add_note(self, db_with_papers):
        conn = get_db(db_with_papers)
        papers = get_papers(conn)
        pid = papers[0]["id"]
        update_reading_status(conn, pid, "reading", notes="Key insight: novel loss function")

        row = conn.execute(
            "SELECT notes FROM reading_status WHERE paper_id = ?", (pid,)
        ).fetchone()
        assert row["notes"] == "Key insight: novel loss function"
        conn.close()

    def test_search_papers(self, db_with_papers):
        conn = get_db(db_with_papers)
        papers = get_papers(conn, limit=200)
        conn.close()
        results = [p for p in papers if "paper 2" in p["title"].lower()]
        assert len(results) == 1
        assert "Test Paper 2" in results[0]["title"]
