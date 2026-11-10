"""Durable validation decisions tied to one output and search/filter policy."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def candidate_key(user: dict[str, str]) -> str:
    # GitHub IDs survive username changes. Fixtures/legacy candidates may lack ID.
    return f"id:{user['id']}" if user.get("id") else user["github_url"].casefold()


class ValidationJournal:
    def __init__(self, output: Path, policy: str, resume: bool = True):
        directory = output.parent / ".scraper-state"
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"{output.stem}.sqlite3"
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS policy (value TEXT NOT NULL)")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS decisions "
            "(identity TEXT PRIMARY KEY, contact_link TEXT NOT NULL, reason TEXT NOT NULL)"
        )
        previous = self.connection.execute("SELECT value FROM policy").fetchone()
        if not resume or previous != (policy,):
            self.connection.execute("DELETE FROM decisions")
            self.connection.execute("DELETE FROM policy")
            self.connection.execute("INSERT INTO policy VALUES (?)", (policy,))
        self.connection.commit()

    def completed(self, saved_links: set[str]) -> set[str]:
        """A saved lead is only complete while its CSV row still exists."""
        rows = self.connection.execute("SELECT identity, contact_link FROM decisions").fetchall()
        missing = [(identity,) for identity, link in rows if link and link not in saved_links]
        with self.connection:
            self.connection.executemany("DELETE FROM decisions WHERE identity = ?", missing)
        return {identity for identity, link in rows if not link or link in saved_links}

    def record(self, outcomes, users: list[dict[str, str]]) -> None:
        # The coordinator calls this only AFTER accepted contacts are durable.
        # Request failures remain retryable and never become permanent rejections.
        rows = [
            (candidate_key(users[outcome.index]),
             outcome.contact.link.casefold() if outcome.contact is not None else "",
             outcome.reason)
            for outcome in outcomes if not outcome.error_message
        ]
        with self.connection:
            self.connection.executemany("INSERT OR REPLACE INTO decisions VALUES (?, ?, ?)", rows)

    def close(self) -> None:
        self.connection.close()


def validation_policy(location_query: str, min_years: int, max_years: int, min_badges: int) -> str:
    return json.dumps({
        "version": 1, "query": location_query,
        "age": [min_years, max_years], "badges_greater_than": min_badges,
        "telegram_required": True,
    }, sort_keys=True)
