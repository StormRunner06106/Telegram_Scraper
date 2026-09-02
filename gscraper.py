#!/usr/bin/env python3
"""Compatibility entrypoint for the interactive scraper agent.

Interactive POSIX runs are placed in a tmux session automatically so a scrape
keeps running when the controlling SSH terminal disconnects.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from githubscraper.agent import main


TMUX_SESSION_NAME = "gscraper"


def run_in_tmux_if_needed() -> int | None:
    """Start or attach to the scraper's tmux session when appropriate.

    ``None`` tells the caller to run the scraper in the current process.  An
    integer is the exit status returned by tmux.
    """
    if (
        os.name == "nt"
        or os.environ.get("TMUX")
        or os.environ.get("GSCRAPER_NO_TMUX") == "1"
        or not sys.stdin.isatty()
        or not sys.stdout.isatty()
    ):
        return None

    tmux = shutil.which("tmux")
    if tmux is None:
        print(
            "Error: tmux is required for an interactive scraper run. "
            "Install tmux, or set GSCRAPER_NO_TMUX=1 to run without it.",
            file=sys.stderr,
        )
        return 1

    scraper_command = shlex.join(
        [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
    )
    print(
        f"Opening tmux session '{TMUX_SESSION_NAME}'. "
        "Detach with Ctrl-b d; reattach with: "
        f"tmux attach -t {TMUX_SESSION_NAME}"
    )
    return subprocess.call(
        [
            tmux,
            "new-session",
            "-A",
            "-s",
            TMUX_SESSION_NAME,
            scraper_command,
        ]
    )


def entrypoint() -> int:
    tmux_status = run_in_tmux_if_needed()
    if tmux_status is not None:
        return tmux_status
    return main()


if __name__ == "__main__":
    raise SystemExit(entrypoint())
