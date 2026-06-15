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


def test_created_date_ranges_target_accounts_between_six_and_twenty_years_old() -> None:
    ranges = created_date_ranges(datetime(2029, 6, 15, tzinfo=timezone.utc))

    assert ranges[0].start == date(2008, 6, 16)
    assert ranges[-1].end == date(2023, 6, 15)
