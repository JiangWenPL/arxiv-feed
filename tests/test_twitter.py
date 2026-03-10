"""Tests for Twitter/X scraper with mocked feeds."""

from unittest.mock import patch, MagicMock
from src.scraper.twitter_scraper import scrape_twitter, _fetch_account, _clean_tweet


class TestCleanTweet:
    def test_removes_html(self):
        assert _clean_tweet("<p>Hello <b>world</b></p>") == "Hello world"

    def test_collapses_whitespace(self):
        assert _clean_tweet("Hello   \n\n  world") == "Hello world"

    def test_empty(self):
        assert _clean_tweet("") == ""


class TestFetchAccount:
    @patch("src.scraper.twitter_scraper.feedparser.parse")
    def test_returns_posts_on_success(self, mock_parse):
        mock_entry = MagicMock()
        mock_entry.get.side_effect = lambda k, d="": {
            "title": "New 3DGS paper just dropped!",
            "link": "https://twitter.com/user/status/123",
            "id": "123",
        }.get(k, d)
        mock_entry.published_parsed = (2026, 3, 10, 12, 0, 0, 0, 69, 0)
        mock_entry.updated_parsed = None

        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]
        mock_feed.bozo = False
        mock_parse.return_value = mock_feed

        account = {"handle": "test_user", "name": "Test User", "credibility": 1}
        posts = _fetch_account(account, "latest_research")
        assert len(posts) == 1
        assert posts[0]["source"] == "twitter"
        assert posts[0]["category"] == "latest_research"
        assert "@test_user" in posts[0]["title"]

    @patch("src.scraper.twitter_scraper.feedparser.parse")
    def test_all_bridges_fail_returns_empty(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feed.bozo = True
        mock_parse.return_value = mock_feed

        account = {"handle": "nobody", "name": "Nobody"}
        posts = _fetch_account(account, "general_reading")
        assert posts == []

    @patch("src.scraper.twitter_scraper.feedparser.parse")
    def test_strips_at_from_handle(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_feed.bozo = True
        mock_parse.return_value = mock_feed

        account = {"handle": "@with_at", "name": "With At"}
        _fetch_account(account, "ml_infra")
        # Should have called with handle without @
        call_url = mock_parse.call_args_list[0][0][0]
        assert "@" not in call_url.split("/")[-2]


class TestScrapeTwitter:
    @patch("src.scraper.twitter_scraper._fetch_account")
    def test_aggregates_categories(self, mock_fetch):
        mock_fetch.return_value = [{"title": "tweet"}]
        config = {
            "twitter": {
                "accounts": {
                    "latest_research": [{"handle": "a", "name": "A"}],
                    "ml_infra": [{"handle": "b", "name": "B"}],
                }
            }
        }
        posts = scrape_twitter(config)
        assert len(posts) == 2
        assert mock_fetch.call_count == 2

    @patch("src.scraper.twitter_scraper._fetch_account")
    def test_empty_config(self, mock_fetch):
        posts = scrape_twitter({"twitter": {"accounts": {}}})
        assert posts == []
        assert mock_fetch.call_count == 0
