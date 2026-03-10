"""Scrape tweets/posts from X/Twitter via RSS bridge services.

Uses public RSS bridge instances (nitter, rss.app) to avoid API costs.
Falls back gracefully if bridges are down.
"""

import feedparser
import logging
from datetime import datetime, timezone
from ..config import load_sources

logger = logging.getLogger(__name__)

# Public RSS bridge endpoints for Twitter/X (try in order)
BRIDGE_TEMPLATES = [
    "https://nitter.net/{handle}/rss",
    "https://nitter.privacydev.net/{handle}/rss",
    "https://twiiit.com/{handle}/rss",
]


def scrape_twitter(config: dict | None = None) -> list[dict]:
    """Fetch recent tweets from configured Twitter/X accounts via RSS bridges."""
    if config is None:
        config = load_sources()

    twitter_cfg = config.get("twitter", {})
    accounts = twitter_cfg.get("accounts", {})
    all_posts = []

    for category_name, account_list in accounts.items():
        for account in account_list:
            posts = _fetch_account(account, category_name)
            all_posts.extend(posts)

    logger.info(f"twitter: fetched {len(all_posts)} tweets total")
    return all_posts


def _fetch_account(account: dict, category: str) -> list[dict]:
    """Try to fetch tweets for a single account via RSS bridges."""
    handle = account["handle"].lstrip("@")
    name = account.get("name", handle)

    for template in BRIDGE_TEMPLATES:
        url = template.format(handle=handle)
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                continue

            posts = []
            for entry in feed.entries[:5]:  # limit per account
                pub_date = _parse_date(entry)
                post_url = entry.get("link", "")
                text = _clean_tweet(entry.get("title", "") or entry.get("summary", ""))

                if not text:
                    continue

                posts.append({
                    "source": "twitter",
                    "source_id": post_url or entry.get("id", ""),
                    "title": f"@{handle}: {text[:120]}",
                    "authors": name,
                    "abstract": text[:500],
                    "url": post_url,
                    "category": category,
                    "subcategory": "twitter",
                    "tags": f"twitter, {handle}",
                    "date_published": pub_date,
                    "credibility": account.get("credibility", 2),
                })

            if posts:
                logger.info(f"  -> {len(posts)} tweets from @{handle} via {template.split('/')[2]}")
                return posts

        except Exception as e:
            logger.debug(f"twitter: bridge {template.split('/')[2]} failed for @{handle}: {e}")
            continue

    logger.warning(f"twitter: all bridges failed for @{handle}")
    return []


def _parse_date(entry) -> str:
    """Extract date from feed entry."""
    from time import mktime
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                dt = datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
                return dt.isoformat()
            except (ValueError, OverflowError):
                pass
    return datetime.now(timezone.utc).isoformat()


def _clean_tweet(text: str) -> str:
    """Clean up tweet text."""
    import re
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text
