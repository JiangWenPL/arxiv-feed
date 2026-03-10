"""Score and rank papers based on relevance heuristics."""

import logging
from ..config import load_authors_whitelist

logger = logging.getLogger(__name__)

# High-value keywords get extra score
KEYWORD_WEIGHTS = {
    # 3DGS (your primary focus)
    "gaussian splatting": 5.0,
    "3dgs": 5.0,
    "3d gaussian": 5.0,
    "nerf": 3.0,
    "neural radiance": 3.0,
    "neural rendering": 3.0,
    "differentiable rendering": 3.0,
    "point-based rendering": 3.0,
    # ML Infra
    "flash attention": 4.0,
    "kv cache": 4.0,
    "quantization": 2.0,
    "inference optimization": 3.0,
    "cuda kernel": 3.0,
    "tensor parallel": 2.5,
    "mixed precision": 2.0,
    # Learning Methods
    "rlhf": 4.0,
    "dpo": 3.5,
    "alignment": 2.5,
    "scaling law": 3.0,
    "chain of thought": 2.5,
    "pretraining": 2.0,
    # General / Math
    "stochastic calculus": 2.0,
    "convex optimization": 2.0,
    "portfolio optimization": 2.0,
}


def score_paper(paper: dict, whitelist: dict | None = None) -> float:
    """Compute a relevance score for a paper."""
    if whitelist is None:
        whitelist = load_authors_whitelist()

    score = 0.0
    title_lower = paper.get("title", "").lower()
    abstract_lower = paper.get("abstract", "").lower()
    authors_lower = paper.get("authors", "").lower()
    text = f"{title_lower} {abstract_lower}"

    # 1. Keyword matching (title counts 2x)
    for keyword, weight in KEYWORD_WEIGHTS.items():
        kw = keyword.lower()
        if kw in title_lower:
            score += weight * 2.0
        elif kw in abstract_lower:
            score += weight

    # 2. Author credibility
    researchers = whitelist.get("researchers", [])
    for researcher in researchers:
        name_lower = researcher["name"].lower()
        # Check if any part of researcher name appears in authors
        name_parts = name_lower.split()
        last_name = name_parts[-1] if name_parts else ""
        if last_name and last_name in authors_lower:
            tier = researcher.get("credibility_tier", 3)
            tier_bonus = {1: 5.0, 2: 3.0, 3: 1.0}.get(tier, 0.5)
            score += tier_bonus
            # Extra bonus if topic overlap
            topics = researcher.get("topics", [])
            for topic in topics:
                if topic.lower() in text:
                    score += 1.0

    # 3. Source credibility bonus
    credibility = paper.get("credibility", 2)
    score += {1: 3.0, 2: 1.0, 3: 0.0}.get(credibility, 0.0)

    # 4. Blog posts from known authors get a flat bonus (always worth reading)
    if paper.get("source") == "blog":
        score += 2.0

    return round(score, 2)


def score_papers(papers: list[dict]) -> list[dict]:
    """Score a list of papers and return them sorted by score descending."""
    whitelist = load_authors_whitelist()
    for paper in papers:
        paper["score"] = score_paper(paper, whitelist)
    papers.sort(key=lambda p: p["score"], reverse=True)
    logger.info(f"scored {len(papers)} papers, top score: {papers[0]['score'] if papers else 0}")
    return papers
