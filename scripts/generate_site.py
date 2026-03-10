#!/usr/bin/env python3
"""Generate static site from the database."""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.site.generator import generate_site

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    out = generate_site()
    print(f"Site generated at: {out}")


if __name__ == "__main__":
    main()
