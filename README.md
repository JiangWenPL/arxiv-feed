# arxiv-feed

Personalized research paper and blog indexing tool. Scrapes arxiv, RSS blogs, and (soon) Twitter/X to surface credible AI research, scored and categorized.

## Quick Start

```bash
cd ~/projects/arxiv-feed
pip install -e .
python scripts/run_all.py     # scrape + generate site + digest
```

## Project Structure

```
src/
  scraper/    - arxiv, RSS, (future: twitter) scrapers
  db/         - SQLite schema and queries
  site/       - Static site generator (Jinja2)
  config/     - sources.yaml, authors_whitelist.yaml
scripts/      - Entry points: scrape.py, generate_site.py, send_digest.py, run_all.py
docs/         - Generated static site (GitHub Pages)
openclaw/     - OpenClaw agent config (SOUL.md, skills)
data/         - SQLite DB (gitignored)
```

## Sections

| Section | Focus |
|---------|-------|
| Latest Research | 3D Gaussian Splatting, neural rendering |
| ML Infra | Flash Attention, KV cache, quantization |
| Learning Methods | RLHF, DPO, alignment, scaling laws |
| General Reading | Math, algorithms, quant finance |

## OpenClaw Integration

The `research-feed` agent delivers digests via Discord at 8 AM and 6 PM. See `openclaw/SOUL.md` for details.

## Status

- [x] Phase 1: Core pipeline (arxiv + RSS + scoring + static site)
- [ ] Phase 2: OpenClaw delivery + reading tracker
- [ ] Phase 3: Twitter/X feed + enhanced scoring
