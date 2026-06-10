"""Regression tests for GitHub search partition handling."""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from githubscraper.core import DateRange, search_github_users


def _fake_users(count: int, prefix: str) -> list[dict[str, str]]:
    return [
        {"username": f"{prefix}{index}", "github_url": f"https://github.com/{prefix}{index}"}
        for index in range(count)
    ]


def test_capped_partition_users_are_kept_before_splitting() -> None:
    """Users from a capped partition must not be dropped when the date range splits."""
    crowded_range = DateRange(start=date(2015, 6, 1), end=date(2015, 6, 2))
    quiet_range = DateRange(start=date(2014, 1, 1), end=date(2014, 1, 1))

    def fake_single_query(location: str, additional_filters: str, token=None):
        if "created:2015-06-01..2015-06-02" in additional_filters:
            return _fake_users(1000, "crowded"), True
        if "created:2014-01-01..2014-01-01" in additional_filters:
            return _fake_users(50, "quiet"), False
        return [], False

    with patch("githubscraper.core.FOLLOWER_RANGES", ["followers:0"]):
        with patch("githubscraper.core.created_date_ranges", return_value=[crowded_range, quiet_range]):
            with patch("githubscraper.core.search_github_users_single_query", side_effect=fake_single_query):
                with patch("githubscraper.core.time.sleep"):
                    users, has_more = search_github_users("Austin, Texas", max_results=10_000)

    usernames = {user["username"] for user in users}
    assert any(username.startswith("crowded") for username in usernames), "capped partition users were discarded"
    assert any(username.startswith("quiet") for username in usernames)
    assert len(usernames) == 1050
    assert has_more is False
