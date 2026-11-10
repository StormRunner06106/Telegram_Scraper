"""Tests for GitHub account age range filtering."""

import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from githubscraper.core import account_age_is_within_required_year_range, created_date_ranges


def test_account_age_range_is_inclusive() -> None:
    assert account_age_is_within_required_year_range(5) is False
    assert account_age_is_within_required_year_range(6) is True
    assert account_age_is_within_required_year_range(20) is True
    assert account_age_is_within_required_year_range(21) is False


def test_discovery_covers_all_ages_and_has_no_date_gaps() -> None:
    ranges = created_date_ranges(datetime(2029, 6, 15, tzinfo=timezone.utc))

    assert ranges[0].start == date(1970, 1, 1)
    assert ranges[-1].end == date(2029, 6, 15)
    assert all((right.start - left.end).days == 1 for left, right in zip(ranges, ranges[1:]))
