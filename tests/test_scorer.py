"""Tests for the relevance scorer."""

from src.scraper.scorer import score_paper, score_papers, KEYWORD_WEIGHTS


# Minimal whitelist for tests (avoids loading YAML)
WHITELIST = {
    "researchers": [
        {"name": "Bernhard Kerbl", "credibility_tier": 1, "topics": ["gaussian splatting"]},
        {"name": "Tri Dao", "credibility_tier": 1, "topics": ["flash attention"]},
        {"name": "Trevor Gale", "credibility_tier": 2, "topics": ["sparse computation"]},
    ]
}


def _paper(**overrides):
    base = {
        "title": "A Generic Paper",
        "abstract": "Nothing special here.",
        "authors": "Jane Doe, John Smith",
        "source": "arxiv",
    }
    base.update(overrides)
    return base


class TestScorePaper:
    def test_no_match_scores_only_credibility(self):
        paper = _paper()
        # Default credibility=2 gives +1.0
        assert score_paper(paper, WHITELIST) == 1.0

    def test_keyword_in_title_gets_double(self):
        paper = _paper(title="Fast Gaussian Splatting for Real-Time Rendering")
        score = score_paper(paper, WHITELIST)
        assert score >= KEYWORD_WEIGHTS["gaussian splatting"] * 2.0

    def test_keyword_in_abstract_only(self):
        paper = _paper(abstract="We improve gaussian splatting with a new approach")
        score = score_paper(paper, WHITELIST)
        expected = KEYWORD_WEIGHTS["gaussian splatting"]
        assert score >= expected
        # Should NOT get double weight
        assert score < expected * 2.0 + 1  # some slack for credibility

    def test_keyword_title_not_double_counted_in_abstract(self):
        """If keyword is in title, it should only count as title (2x), not also abstract."""
        paper = _paper(title="Flash Attention Rocks", abstract="No keywords here.")
        score = score_paper(paper, WHITELIST)
        # title match (4.0 * 2) + credibility bonus (1.0) = 9.0
        assert score == KEYWORD_WEIGHTS["flash attention"] * 2.0 + 1.0

    def test_multiple_keywords_stack(self):
        paper = _paper(
            title="Flash Attention for Neural Rendering",
            abstract="We combine flash attention with gaussian splatting",
        )
        score = score_paper(paper, WHITELIST)
        assert score > 10.0  # multiple high-value keywords

    def test_author_tier1_bonus(self):
        paper = _paper(authors="Bernhard Kerbl, Someone Else")
        score = score_paper(paper, WHITELIST)
        assert score >= 5.0  # tier1 bonus

    def test_author_tier2_bonus(self):
        paper = _paper(authors="Trevor Gale")
        score = score_paper(paper, WHITELIST)
        assert score >= 3.0  # tier2 bonus

    def test_author_topic_overlap_bonus(self):
        paper = _paper(
            authors="Bernhard Kerbl",
            abstract="New gaussian splatting method",
        )
        score = score_paper(paper, WHITELIST)
        # tier1 (5.0) + topic overlap (1.0) + keyword in abstract (5.0)
        assert score >= 11.0

    def test_blog_source_bonus(self):
        paper = _paper(source="blog")
        score_blog = score_paper(paper, WHITELIST)
        paper_arxiv = _paper(source="arxiv")
        score_arxiv = score_paper(paper_arxiv, WHITELIST)
        assert score_blog - score_arxiv == 2.0

    def test_credibility_bonus(self):
        paper_t1 = _paper(credibility=1)
        paper_t3 = _paper(credibility=3)
        s1 = score_paper(paper_t1, WHITELIST)
        s3 = score_paper(paper_t3, WHITELIST)
        assert s1 - s3 == 3.0

    def test_score_below_threshold_is_noise(self):
        paper = _paper()
        score = score_paper(paper, WHITELIST)
        assert score < 2.0  # noise threshold


class TestScorePapers:
    def test_sorts_descending(self):
        papers = [
            _paper(title="Boring paper"),
            _paper(title="Gaussian Splatting Breakthrough"),
            _paper(title="Flash Attention v3"),
        ]
        scored = score_papers(papers)
        scores = [p["score"] for p in scored]
        assert scores == sorted(scores, reverse=True)

    def test_adds_score_field(self):
        papers = [_paper()]
        scored = score_papers(papers)
        assert "score" in scored[0]

    def test_empty_list(self):
        assert score_papers([]) == []
