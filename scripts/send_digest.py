#!/usr/bin/env python3
"""Generate a text digest of top unread papers (for OpenClaw to deliver)."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.models import init_db, get_db, get_digest

CATEGORY_LABELS = {
    "latest_research": "Latest Research (3DGS)",
    "ml_infra": "ML Infra",
    "learning_methods": "Learning Methods",
    "general_reading": "General Reading",
}


def format_digest(papers: list[dict], limit: int = 8) -> str:
    """Format papers into a readable digest string."""
    if not papers:
        return "No new papers to read today."

    # Group by category
    by_cat = {}
    for p in papers[:limit]:
        cat = p.get("category", "other")
        by_cat.setdefault(cat, []).append(p)

    lines = ["**Research Digest**\n"]

    for cat, cat_papers in by_cat.items():
        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(f"**{label}**")
        for p in cat_papers:
            score_str = f"[{p['score']:.0f}]" if p.get("score") else ""
            title = p["title"]
            url = p["url"]
            authors_short = p["authors"].split(",")[0].strip()
            if "et al" not in authors_short and "," in p["authors"]:
                authors_short += " et al."
            lines.append(f"  {score_str} {title}")
            lines.append(f"    {authors_short} | <{url}>")
        lines.append("")

    lines.append(f"_{len(papers)} papers total — read more on the site_")
    return "\n".join(lines)


def main():
    init_db()
    conn = get_db()
    papers = get_digest(conn, limit=10)
    conn.close()

    digest = format_digest(papers)
    print(digest)

    # Also write as JSON for programmatic use
    digest_path = Path(__file__).parent.parent / "data" / "latest_digest.json"
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text(json.dumps({
        "text": digest,
        "count": len(papers),
        "papers": [{"title": p["title"], "url": p["url"], "score": p.get("score", 0)} for p in papers],
    }, indent=2))


if __name__ == "__main__":
    main()
