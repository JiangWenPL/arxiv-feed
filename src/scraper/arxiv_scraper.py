"""Scrape papers from arxiv using the official API."""

import arxiv
import logging
from datetime import datetime, timedelta, timezone
from ..config import load_sources

logger = logging.getLogger(__name__)


def scrape_arxiv(config: dict | None = None) -> list[dict]:
    """Fetch recent papers from arxiv based on configured queries."""
    if config is None:
        config = load_sources()

    arxiv_cfg = config["arxiv"]
    max_results = arxiv_cfg.get("max_results_per_query", 20)
    days_back = arxiv_cfg.get("days_lookback", 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    all_papers = []
    seen_ids = set()

    for category_name, query_list in arxiv_cfg["queries"].items():
        for q in query_list:
            papers = _run_query(q, category_name, max_results, cutoff, seen_ids)
            all_papers.extend(papers)

    logger.info(f"arxiv: fetched {len(all_papers)} papers total")
    return all_papers


def _run_query(
    q: dict, category_name: str, max_results: int, cutoff: datetime, seen_ids: set
) -> list[dict]:
    """Run a single arxiv query and return normalized paper dicts."""
    cat = q["category"]
    keywords = q["keywords"]
    subcategory = q.get("subcategory", "")

    # Build query: category + keyword OR
    kw_query = " OR ".join(f'all:"{kw}"' for kw in keywords)
    query_str = f"cat:{cat} AND ({kw_query})"

    logger.info(f"arxiv query: {query_str[:80]}...")

    client = arxiv.Client()
    search = arxiv.Search(
        query=query_str,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    papers = []
    try:
        for result in client.results(search):
            pub_date = result.published
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            if pub_date < cutoff:
                continue

            arxiv_id = result.entry_id.split("/abs/")[-1]
            if arxiv_id in seen_ids:
                continue
            seen_ids.add(arxiv_id)

            authors_str = ", ".join(a.name for a in result.authors[:10])
            if len(result.authors) > 10:
                authors_str += f" et al. ({len(result.authors)} authors)"

            # categories is a list of strings in arxiv>=2.0
            cats = result.categories if hasattr(result, "categories") else [cat]
            tags_str = ", ".join(str(c) for c in cats) if cats else cat

            papers.append({
                "source": "arxiv",
                "source_id": arxiv_id,
                "title": result.title.replace("\n", " ").strip(),
                "authors": authors_str,
                "abstract": (result.summary or "").replace("\n", " ").strip()[:1000],
                "url": result.entry_id,
                "category": category_name,
                "subcategory": subcategory,
                "tags": tags_str,
                "date_published": pub_date.isoformat(),
            })
    except Exception as e:
        logger.warning(f"arxiv query failed for {cat}: {e}")

    logger.info(f"  -> {len(papers)} papers from {cat} [{', '.join(keywords[:3])}...]")
    return papers
