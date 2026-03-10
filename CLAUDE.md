# CLAUDE.md — arxiv-feed

Personalized research paper indexing tool. Python 3.10+, SQLite, Jinja2 static site.

## Quick Reference
- Run full pipeline: `python scripts/run_all.py`
- Run scraper only: `python scripts/scrape.py`
- Generate site: `python scripts/generate_site.py`
- Generate digest: `python scripts/send_digest.py`
- Install: `pip install -e .`

## Project Layout
- `src/scraper/` — arxiv + RSS scrapers
- `src/db/models.py` — SQLite schema and all DB operations
- `src/scraper/scorer.py` — relevance scoring heuristic
- `src/config/` — sources.yaml (queries, feeds) + authors_whitelist.yaml
- `src/site/` — Jinja2 static site generator, templates in templates/
- `scripts/` — CLI entry points
- `openclaw/` — OpenClaw agent config (SOUL.md, HEARTBEAT.md)
- `docs/` — generated static site for GitHub Pages
- `data/feed.db` — SQLite DB (gitignored, private)

## Conventions
- Keep it simple. No frameworks, no over-engineering.
- Public site (docs/) must NEVER contain personal data (reading status, notes, tokens).
- Config changes go in YAML files, not hardcoded.
- Score threshold: papers with score < 2.0 are low-relevance noise.

## OpenClaw
- Agent ID: research-feed
- Delivery: Discord (8 AM, 6 PM)
- Agent workspace: ~/projects/arxiv-feed
- See openclaw/SOUL.md for agent behavior spec
