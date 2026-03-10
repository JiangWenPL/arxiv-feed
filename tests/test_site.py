"""Tests for the static site generator."""

import pytest
from src.db.models import get_db, init_db, add_paper
from src.site.generator import generate_site, SECTIONS


@pytest.fixture
def site_db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = get_db(db_path)
    # Seed papers across sections
    for i, section in enumerate(SECTIONS):
        for j in range(3):
            add_paper(
                conn,
                source="arxiv",
                source_id=f"{section['id']}-{j}",
                title=f"Paper {j} in {section['title']}",
                authors="Author A",
                url=f"https://arxiv.org/abs/test-{i}-{j}",
                category=section["id"],
                abstract=f"Abstract for paper {j}",
                score=float(10 - j),
            )
    conn.close()
    return db_path


class TestGenerateSite:
    def test_creates_output_files(self, site_db, tmp_path, monkeypatch):
        out_dir = tmp_path / "docs"
        monkeypatch.setattr("src.site.generator.OUTPUT_DIR", out_dir)
        generate_site(db_path=site_db)
        assert (out_dir / "index.html").exists()
        assert (out_dir / "style.css").exists()

    def test_html_contains_all_sections(self, site_db, tmp_path, monkeypatch):
        out_dir = tmp_path / "docs"
        monkeypatch.setattr("src.site.generator.OUTPUT_DIR", out_dir)
        generate_site(db_path=site_db)
        html = (out_dir / "index.html").read_text()
        for section in SECTIONS:
            assert section["title"] in html
            assert f'id="{section["id"]}"' in html

    def test_html_contains_papers(self, site_db, tmp_path, monkeypatch):
        out_dir = tmp_path / "docs"
        monkeypatch.setattr("src.site.generator.OUTPUT_DIR", out_dir)
        generate_site(db_path=site_db)
        html = (out_dir / "index.html").read_text()
        assert "Paper 0 in Latest Research" in html
        assert "Author A" in html

    def test_no_personal_data_in_output(self, site_db, tmp_path, monkeypatch):
        """Public site must not leak reading status or notes."""
        out_dir = tmp_path / "docs"
        monkeypatch.setattr("src.site.generator.OUTPUT_DIR", out_dir)
        # Add a reading status with notes
        conn = get_db(site_db)
        from src.db.models import update_reading_status

        papers = conn.execute("SELECT id FROM papers LIMIT 1").fetchone()
        update_reading_status(conn, papers["id"], "reading", notes="secret note")
        conn.close()

        generate_site(db_path=site_db)
        html = (out_dir / "index.html").read_text()
        assert "secret note" not in html
        # Status values like "reading", "done", "unread" should not appear as data attributes
        assert 'status="reading"' not in html
        assert "unread" not in html.lower()

    def test_empty_db_still_renders(self, tmp_path, monkeypatch):
        db_path = tmp_path / "empty.db"
        init_db(db_path)
        out_dir = tmp_path / "docs"
        monkeypatch.setattr("src.site.generator.OUTPUT_DIR", out_dir)
        generate_site(db_path=db_path)
        html = (out_dir / "index.html").read_text()
        assert "0 papers" in html
