"""Enrich paper scores with citation data from Semantic Scholar API.

Uses the free (no API key) Semantic Scholar API with rate limiting.
"""

import logging
import time
from urllib.request import urlopen, Request
from urllib.error import URLError
import json

logger = logging.getLogger(__name__)

S2_API = "https://api.semanticscholar.org/graph/v1/paper"
RATE_LIMIT_DELAY = 1.0  # seconds between requests (free tier: ~100/5min)


def enrich_with_citations(papers: list[dict], max_lookups: int = 30) -> list[dict]:
    """Add citation-based score boosts to papers.

    Only looks up arxiv papers (blogs don't have S2 entries).
    Applies a logarithmic citation bonus to avoid overly weighting old papers.
    """
    import math

    lookup_count = 0
    for paper in papers:
        if paper.get("source") != "arxiv":
            continue
        if lookup_count >= max_lookups:
            break

        source_id = paper.get("source_id", "")
        if not source_id:
            continue

        citation_count = _get_citation_count(source_id)
        if citation_count is not None and citation_count > 0:
            # Log scale: 10 citations = +2.3, 100 = +4.6, 1000 = +6.9
            bonus = round(math.log10(citation_count + 1) * 2.0, 2)
            paper["citation_count"] = citation_count
            paper["citation_bonus"] = bonus
            paper["score"] = round(paper.get("score", 0) + bonus, 2)
            logger.debug(f"citations: {source_id} has {citation_count} cites, +{bonus}")

        lookup_count += 1

    logger.info(f"citations: enriched {lookup_count} papers")
    return papers


def _get_citation_count(arxiv_id: str) -> int | None:
    """Look up citation count from Semantic Scholar."""
    # Clean arxiv ID (remove version suffix like v1, v2)
    clean_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
    url = f"{S2_API}/ARXIV:{clean_id}?fields=citationCount"

    try:
        req = Request(url, headers={"User-Agent": "arxiv-feed/0.1 (research tool)"})
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            time.sleep(RATE_LIMIT_DELAY)
            return data.get("citationCount")
    except (URLError, json.JSONDecodeError, TimeoutError) as e:
        logger.debug(f"citations: S2 lookup failed for {arxiv_id}: {e}")
        time.sleep(RATE_LIMIT_DELAY)
        return None
