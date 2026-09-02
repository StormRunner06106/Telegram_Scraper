#!/usr/bin/env python3
"""Validate the local GitHub and Ray scraper configuration."""

from __future__ import annotations

import os
from pathlib import Path

from githubscraper.core import load_env_file


def mask_value(value: str, show_chars: int = 10) -> str:
    if not value:
        return "(not set)"
    if len(value) <= show_chars:
        return "*" * len(value)
    return value[:show_chars] + "..." + "*" * (len(value) - show_chars)


def main() -> int:
    print("=" * 60)
    print("GitHub Location Scraper - Environment Check")
    print("=" * 60)

    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        load_env_file(env_file)
        print(f"Environment file: {env_file}")
    else:
        print("Environment file not found. Copy .env.example to .env.")

    github_token = os.getenv("GITHUB_TOKEN", "")
    if github_token and github_token != "your_github_token_here":
        print(f"GITHUB_TOKEN: {mask_value(github_token, 15)}")
        token_ready = True
    else:
        print("GITHUB_TOKEN: not configured")
        token_ready = False

    delay = os.getenv("SCRAPE_DELAY_SECONDS", "1.0")
    print(f"SCRAPE_DELAY_SECONDS: {delay}")

    try:
        import ray

        print(f"Ray: {ray.__version__}")
    except ImportError:
        print("Ray: not installed (run: python -m pip install -r requirements.txt)")
        return 1

    if not token_ready:
        print("Add a GitHub token to .env for practical API quotas.")
        print("Configuration check completed with a warning.")
        return 0

    print("Configuration is ready. Run: python gscraper.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
