#!/usr/bin/env python3
"""Main scraping entry point. Fetches from all sources, scores, and stores."""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.models import init_db, get_db, add_paper
from src.scraper.arxiv_scraper import scrape_arxiv
from src.scraper.rss_scraper import scrape_rss
from src.scraper.twitter_scraper import scrape_twitter
from src.scraper.scorer import score_papers
from src.scraper.citation_enricher import enrich_with_citations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scrape")


def main():
    logger.info("=== arxiv-feed scraper starting ===")

    # Initialize DB
    init_db()
    conn = get_db()

    # Collect from all sources
    papers = []

    logger.info("--- Fetching from arxiv ---")
    papers.extend(scrape_arxiv())

    logger.info("--- Fetching from RSS feeds ---")
    papers.extend(scrape_rss())

    logger.info("--- Fetching from Twitter/X ---")
    papers.extend(scrape_twitter())

    if not papers:
        logger.warning("No papers fetched from any source")
        conn.close()
        return

    # Score all papers
    logger.info(f"--- Scoring {len(papers)} papers ---")
    papers = score_papers(papers)

    # Enrich top papers with citation data
    logger.info("--- Enriching with citation data ---")
    papers = enrich_with_citations(papers, max_lookups=30)

    # Store in DB
    new_count = 0
    for paper in papers:
        row_id = add_paper(
            conn,
            source=paper["source"],
            source_id=paper["source_id"],
            title=paper["title"],
            authors=paper["authors"],
            url=paper["url"],
            category=paper["category"],
            abstract=paper.get("abstract", ""),
            subcategory=paper.get("subcategory", ""),
            tags=paper.get("tags", ""),
            score=paper.get("score", 0.0),
            date_published=paper.get("date_published", ""),
        )
        if row_id is not None:
            new_count += 1

    conn.close()
    logger.info(f"=== Done: {new_count} new papers added (out of {len(papers)} fetched) ===")


if __name__ == "__main__":
    main()
