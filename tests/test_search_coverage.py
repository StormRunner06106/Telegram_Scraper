"""Coverage regressions for location scope, crowded searches and API timeouts."""

from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from githubscraper import core


def item(number):
    return {"id": number, "login": f"user{number}", "html_url": f"https://github.com/user{number}"}


@pytest.mark.parametrize("location,expected", [
    ("Dallas, Texas, United States", 'type:user location:"Dallas"'),
    ("Dallas, TX", 'type:user location:"Dallas"'),
    ("Salt Lake City, Utah, United States", 'type:user location:"Salt Lake City"'),
    ("United States", 'type:user location:"United States"'),
    ("United Kingdom", 'type:user location:"United Kingdom"'),
])
def test_one_location_qualifier_prevents_statewide_or_matches(location, expected):
    assert core.build_location_query(location) == expected


def test_reads_every_page_once_with_explicit_sort(monkeypatch):
    pages = []

    def request(url, headers):
        query = parse_qs(urlparse(url).query)
        page = int(query["page"][0])
        assert query["sort"] == ["joined"]
        assert query["order"] == ["asc"]
        pages.append(page)
        begin = (page - 1) * 100
        return {"total_count": 205, "items": [item(i) for i in range(begin, min(begin + 100, 205))]}, {}

    monkeypatch.setattr(core, "request_json_response", request)
    users, incomplete = core.search_github_users_single_query("Dallas", "")
    assert pages == [1, 2, 3]
    assert len(users) == 205
    assert not incomplete


def test_capped_parent_does_not_waste_ten_pages_before_splitting(monkeypatch):
    calls = []

    def request(url, headers):
        calls.append(url)
        return {"total_count": 5000, "items": [item(i) for i in range(100)]}, {}

    monkeypatch.setattr(core, "request_json_response", request)
    users, incomplete = core.search_github_users_single_query("Dallas", "")
    assert len(calls) == 1
    assert len(users) == 100
    assert incomplete


@pytest.mark.parametrize("total,items", [(0, []), (10, [item(1)])])
def test_incomplete_results_are_retried_then_reported(monkeypatch, total, items):
    attempts = []

    def request(url, headers):
        attempts.append(url)
        return {"total_count": total, "items": items, "incomplete_results": True}, {}

    monkeypatch.setattr(core, "request_json_response", request)
    monkeypatch.setattr(core.time, "sleep", lambda _: None)
    _, incomplete = core.search_github_users_single_query("Dallas", "")
    assert len(attempts) == 3
    assert incomplete


def test_truncated_and_duplicate_pages_cannot_be_declared_complete(monkeypatch):
    def request(url, headers):
        return {"total_count": 150, "items": [item(i) for i in range(100)]}, {}

    monkeypatch.setattr(core, "request_json_response", request)
    users, incomplete = core.search_github_users_single_query("Dallas", "")
    assert len(users) == 100
    assert incomplete


def test_crowded_single_day_is_split_by_time_without_losing_boundaries(monkeypatch):
    day = core.DateRange(date(2026, 11, 1), date(2026, 11, 1))
    partitions = []
    monkeypatch.setattr(core, "created_date_ranges", lambda: [day])
    monkeypatch.setattr(core.time, "sleep", lambda _: None)

    def search(location, filters, token):
        partitions.append(filters)
        if "T" not in filters:
            return [], True
        return [{"username": filters, "github_url": filters}], False

    monkeypatch.setattr(core, "search_github_users_single_query", search)
    users, incomplete = core.search_github_users("Dallas")
    assert len(users) == 2
    assert not incomplete
    assert any("T00:00:00+00:00..2026-11-01T11:59:59+00:00" in part for part in partitions)
    assert any("T12:00:00+00:00..2026-11-01T23:59:59+00:00" in part for part in partitions)


def test_second_precision_split_has_no_overlap_or_gap():
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    left, right = core.split_search_range(core.TimeRange(start, start + timedelta(seconds=2)))
    assert left.start == start
    assert right.end == start + timedelta(seconds=2)
    assert right.start - left.end == timedelta(seconds=1)
    assert core.split_search_range(core.TimeRange(start, start)) is None


def test_exhausted_partition_dimensions_report_incomplete(monkeypatch):
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(core, "created_date_ranges", lambda: [core.TimeRange(start, start)])
    monkeypatch.setattr(core, "search_github_users_single_query", lambda *args: ([], True))
    monkeypatch.setattr(core.time, "sleep", lambda _: None)
    users, incomplete = core.search_github_users("Dallas")
    assert not users
    assert incomplete
