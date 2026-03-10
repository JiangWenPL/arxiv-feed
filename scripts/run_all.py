#!/usr/bin/env python3
"""Full pipeline: scrape -> score -> generate site -> produce digest."""

import sys
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def run(script_name: str):
    print(f"\n{'='*60}")
    print(f"Running {script_name}...")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script_name)],
        cwd=str(SCRIPTS_DIR.parent),
    )
    if result.returncode != 0:
        print(f"ERROR: {script_name} failed with code {result.returncode}")
        sys.exit(1)


def main():
    run("scrape.py")
    run("generate_site.py")
    run("send_digest.py")
    print("\n=== Full pipeline complete ===")


if __name__ == "__main__":
    main()
