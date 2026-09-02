"""Tests for the durable tmux launcher."""

from __future__ import annotations

import os
from types import SimpleNamespace

import gscraper


class _TTY:
    def isatty(self) -> bool:
        return True

    def write(self, value: str) -> int:
        return len(value)

    def flush(self) -> None:
        pass


def _set_posix(monkeypatch) -> None:
    monkeypatch.setattr(
        gscraper,
        "os",
        SimpleNamespace(name="posix", environ=os.environ),
    )


def test_existing_tmux_session_runs_scraper_directly(monkeypatch):
    monkeypatch.setenv("TMUX", "/tmp/tmux-1000/default,1,0")
    _set_posix(monkeypatch)

    assert gscraper.run_in_tmux_if_needed() is None


def test_interactive_posix_run_opens_named_tmux_session(monkeypatch):
    calls: list[list[str]] = []
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("GSCRAPER_NO_TMUX", raising=False)
    _set_posix(monkeypatch)
    monkeypatch.setattr(gscraper.sys, "stdin", _TTY())
    monkeypatch.setattr(gscraper.sys, "stdout", _TTY())
    monkeypatch.setattr(gscraper.shutil, "which", lambda command: "/usr/bin/tmux")
    monkeypatch.setattr(gscraper.sys, "argv", ["gscraper.py"])
    monkeypatch.setattr(
        gscraper.subprocess,
        "call",
        lambda command: calls.append(command) or 0,
    )

    assert gscraper.run_in_tmux_if_needed() == 0
    assert calls == [
        [
            "/usr/bin/tmux",
            "new-session",
            "-A",
            "-s",
            "gscraper",
            gscraper.shlex.join(
                [gscraper.sys.executable, str(gscraper.Path(gscraper.__file__).resolve())]
            ),
        ]
    ]


def test_missing_tmux_stops_interactive_posix_run(monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("GSCRAPER_NO_TMUX", raising=False)
    _set_posix(monkeypatch)
    monkeypatch.setattr(gscraper.sys, "stdin", _TTY())
    monkeypatch.setattr(gscraper.sys, "stdout", _TTY())
    monkeypatch.setattr(gscraper.shutil, "which", lambda command: None)

    assert gscraper.run_in_tmux_if_needed() == 1


def test_noninteractive_run_does_not_require_tmux(monkeypatch):
    monkeypatch.delenv("TMUX", raising=False)
    _set_posix(monkeypatch)
    monkeypatch.setattr(gscraper.sys.stdin, "isatty", lambda: False)

    assert gscraper.run_in_tmux_if_needed() is None
