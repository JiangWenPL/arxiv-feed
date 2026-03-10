"""Tests for citation enrichment."""

import json
from unittest.mock import patch, MagicMock
from src.scraper.citation_enricher import enrich_with_citations, _get_citation_count


class TestGetCitationCount:
    @patch("src.scraper.citation_enricher.urlopen")
    def test_returns_count(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"citationCount": 42}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        count = _get_citation_count("2403.00001")
        assert count == 42

    @patch("src.scraper.citation_enricher.urlopen")
    def test_returns_none_on_error(self, mock_urlopen):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("not found")
        count = _get_citation_count("9999.99999")
        assert count is None


class TestEnrichWithCitations:
    @patch("src.scraper.citation_enricher._get_citation_count")
    def test_adds_bonus_to_scored_papers(self, mock_count):
        mock_count.return_value = 100  # log10(101)*2 ≈ 4.01
        papers = [
            {"source": "arxiv", "source_id": "2403.00001", "score": 10.0},
        ]
        result = enrich_with_citations(papers, max_lookups=5)
        assert result[0]["score"] > 10.0
        assert result[0]["citation_count"] == 100
        assert "citation_bonus" in result[0]

    @patch("src.scraper.citation_enricher._get_citation_count")
    def test_skips_blog_posts(self, mock_count):
        papers = [
            {"source": "blog", "source_id": "https://example.com", "score": 5.0},
        ]
        result = enrich_with_citations(papers, max_lookups=5)
        assert result[0]["score"] == 5.0
        mock_count.assert_not_called()

    @patch("src.scraper.citation_enricher._get_citation_count")
    def test_respects_max_lookups(self, mock_count):
        mock_count.return_value = 10
        papers = [
            {"source": "arxiv", "source_id": f"2403.{i:05d}", "score": 1.0}
            for i in range(10)
        ]
        enrich_with_citations(papers, max_lookups=3)
        assert mock_count.call_count == 3

    @patch("src.scraper.citation_enricher._get_citation_count")
    def test_handles_zero_citations(self, mock_count):
        mock_count.return_value = 0
        papers = [
            {"source": "arxiv", "source_id": "2403.00001", "score": 10.0},
        ]
        result = enrich_with_citations(papers, max_lookups=5)
        assert result[0]["score"] == 10.0  # no bonus for 0 citations

    @patch("src.scraper.citation_enricher._get_citation_count")
    def test_handles_none_response(self, mock_count):
        mock_count.return_value = None
        papers = [
            {"source": "arxiv", "source_id": "2403.00001", "score": 10.0},
        ]
        result = enrich_with_citations(papers, max_lookups=5)
        assert result[0]["score"] == 10.0  # unchanged
