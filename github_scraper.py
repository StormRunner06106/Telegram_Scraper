#!/usr/bin/env python3
"""Compatibility entrypoint for the GitHub scraper CLI."""

from githubscraper.core import *  # noqa: F401,F403
from githubscraper.core import main


if __name__ == "__main__":
    raise SystemExit(main())

