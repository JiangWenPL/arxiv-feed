"""Tests for scrapers with mocked external calls."""

from unittest.mock import patch, MagicMock
from src.scraper.rss_scraper import scrape_rss, _fetch_feed, _strip_html, _parse_date


class TestStripHtml:
    def test_removes_tags(self):
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_collapses_whitespace(self):
        assert _strip_html("Hello   \n\n  world") == "Hello world"

    def test_empty_string(self):
        assert _strip_html("") == ""


class TestParseDate:
    def test_published_parsed(self):
        entry = MagicMock()
        entry.published_parsed = (2026, 3, 10, 12, 0, 0, 0, 69, 0)
        entry.updated_parsed = None
        entry.created_parsed = None
        result = _parse_date(entry)
        assert "2026-03-10" in result

    def test_falls_back_to_now(self):
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = None
        entry.created_parsed = None
        result = _parse_date(entry)
        # Should be a recent ISO timestamp
        assert "T" in result


class TestFetchFeed:
    @patch("src.scraper.rss_scraper.feedparser.parse")
    def test_parses_entries(self, mock_parse):
        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda k, d="": {
            "title": "Test Post",
            "link": "https://example.com/post",
            "id": "post-1",
        }.get(k, d)
        mock_entry.summary = "A <b>great</b> summary"
        mock_entry.published_parsed = (2026, 3, 10, 12, 0, 0, 0, 69, 0)
        mock_entry.updated_parsed = None
        mock_entry.created_parsed = None

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]
        mock_feed.bozo = False
        mock_parse.return_value = mock_feed

        feed_cfg = {
            "name": "Test Blog",
            "url": "https://example.com/feed",
            "category": "general_reading",
            "credibility": 1,
        }
        posts = _fetch_feed(feed_cfg)
        assert len(posts) == 1
        assert posts[0]["title"] == "Test Post"
        assert posts[0]["source"] == "blog"
        assert posts[0]["credibility"] == 1

    @patch("src.scraper.rss_scraper.feedparser.parse")
    def test_handles_feed_error(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("bad feed")
        mock_parse.return_value = mock_feed

        feed_cfg = {"name": "Bad", "url": "https://bad.com/feed"}
        posts = _fetch_feed(feed_cfg)
        assert posts == []


class TestScrapeRss:
    @patch("src.scraper.rss_scraper._fetch_feed")
    def test_aggregates_all_feeds(self, mock_fetch):
        mock_fetch.return_value = [{"title": "post"}]
        config = {"blogs": {"feeds": [{"name": "a"}, {"name": "b"}]}}
        posts = scrape_rss(config)
        assert len(posts) == 2
        assert mock_fetch.call_count == 2
