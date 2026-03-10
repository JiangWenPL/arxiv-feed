"""Scrape blog posts from RSS feeds."""

import feedparser
import logging
from datetime import datetime, timezone
from time import mktime
from ..config import load_sources

logger = logging.getLogger(__name__)


def scrape_rss(config: dict | None = None) -> list[dict]:
    """Fetch recent blog posts from configured RSS feeds."""
    if config is None:
        config = load_sources()

    feeds = config.get("blogs", {}).get("feeds", [])
    all_posts = []

    for feed_cfg in feeds:
        posts = _fetch_feed(feed_cfg)
        all_posts.extend(posts)

    logger.info(f"rss: fetched {len(all_posts)} blog posts total")
    return all_posts


def _fetch_feed(feed_cfg: dict) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    name = feed_cfg["name"]
    url = feed_cfg["url"]
    category = feed_cfg.get("category", "general_reading")
    credibility = feed_cfg.get("credibility", 2)

    logger.info(f"rss: fetching {name} from {url}")

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        logger.warning(f"rss: failed to parse {name}: {e}")
        return []

    if feed.bozo and not feed.entries:
        logger.warning(f"rss: feed error for {name}: {feed.bozo_exception}")
        return []

    posts = []
    for entry in feed.entries[:10]:  # limit per feed
        pub_date = _parse_date(entry)
        post_url = entry.get("link", "")
        source_id = post_url or entry.get("id", entry.get("title", ""))

        # Extract summary
        summary = ""
        if hasattr(entry, "summary"):
            summary = _strip_html(entry.summary)[:500]
        elif hasattr(entry, "description"):
            summary = _strip_html(entry.description)[:500]

        posts.append({
            "source": "blog",
            "source_id": source_id,
            "title": entry.get("title", "Untitled").strip(),
            "authors": name,
            "abstract": summary,
            "url": post_url,
            "category": category,
            "subcategory": "blog",
            "tags": f"blog, {name}",
            "date_published": pub_date,
            "credibility": credibility,
        })

    logger.info(f"  -> {len(posts)} posts from {name}")
    return posts


def _parse_date(entry) -> str:
    """Extract publication date from a feed entry."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                dt = datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
                return dt.isoformat()
            except (ValueError, OverflowError):
                pass
    return datetime.now(timezone.utc).isoformat()


def _strip_html(text: str) -> str:
    """Cheap HTML tag removal."""
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()
