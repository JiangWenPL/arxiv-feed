"""Configuration loading utilities."""

import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).parent


def load_sources() -> dict:
    with open(CONFIG_DIR / "sources.yaml") as f:
        return yaml.safe_load(f)


def load_authors_whitelist() -> dict:
    with open(CONFIG_DIR / "authors_whitelist.yaml") as f:
        return yaml.safe_load(f)
