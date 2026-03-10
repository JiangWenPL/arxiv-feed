"""Generate static HTML site from the paper database."""

import logging
from pathlib import Path
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader
from ..db.models import get_db, get_papers

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "docs"

SECTIONS = [
    {
        "id": "latest_research",
        "title": "Latest Research",
        "description": "3D Gaussian Splatting, Neural Rendering, and related work",
    },
    {
        "id": "ml_infra",
        "title": "AI Foundation: ML Infra",
        "description": "Flash Attention, KV Cache, Quantization, Efficient Serving",
    },
    {
        "id": "learning_methods",
        "title": "AI Foundation: Learning Methods",
        "description": "RLHF, DPO, Alignment, Pretraining, Scaling Laws",
    },
    {
        "id": "general_reading",
        "title": "General Reading",
        "description": "Math, Algorithms, Quantitative Finance",
    },
]


def generate_site(db_path=None):
    """Generate the full static site."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )

    conn = get_db(db_path)

    # Build section data
    sections_data = []
    for section in SECTIONS:
        papers = get_papers(conn, category=section["id"], limit=30)
        sections_data.append({**section, "papers": papers, "count": len(papers)})

    total = sum(s["count"] for s in sections_data)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Render index
    template = env.get_template("index.html")
    html = template.render(
        sections=sections_data,
        total=total,
        generated_at=generated_at,
    )

    out_path = OUTPUT_DIR / "index.html"
    out_path.write_text(html)
    logger.info(f"site: wrote {out_path} ({total} papers)")

    # Copy CSS
    css_src = TEMPLATE_DIR / "style.css"
    if css_src.exists():
        (OUTPUT_DIR / "style.css").write_text(css_src.read_text())

    conn.close()
    return out_path
