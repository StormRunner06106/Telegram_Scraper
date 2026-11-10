"""Follow location discovery through real validation and qualified-only CSV writes."""

import json
from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from githubscraper import core


def profile_card(username):
    return f'''<div class="tgme_page_title"><span dir="auto">Test Person</span></div>
    <div class="tgme_page_extra">@{username}</div>'''


@pytest.mark.parametrize("page,expected", [
    (profile_card("example"), True),
    (profile_card("EXAMPLE"), True),
    (profile_card("example_other"), False),
    (profile_card("someone_else") + "you can contact @example right away", False),
    ("If you have Telegram, you can contact @example right away.", False),
    ('<div class="tgme_page_title">Channel</div><div class="tgme_page_extra">300 subscribers</div>', False),
])
def test_telegram_requires_explicit_exact_username(monkeypatch, page, expected):
    monkeypatch.setattr(core, "request_text", lambda *a, **kw: page)
    assert core.telegram_account_exists("example")[0] is expected


def test_unusable_telegram_username_cannot_be_saved(monkeypatch):
    monkeypatch.setattr(core, "request_text", lambda *a, **kw: pytest.fail("Invalid handle requested"))
    assert core.telegram_account_exists("github-with-hyphens") == (False, "")


@pytest.mark.parametrize("mode", ["region", "custom"])
def test_entire_location_is_screened_beyond_1000_and_only_telegram_matches_saved(
    monkeypatch, tmp_path, mode,
):
    total = 1505
    matching = {0, 500, 1000, 1504}  # Includes a match at the very end of discovery.
    profile_calls = []
    telegram_calls = []
    monkeypatch.setattr(core, "REGION_STATE_DIR", tmp_path / "states")
    monkeypatch.setattr(core, "STATE_FILE", tmp_path / "legacy.json")
    monkeypatch.setattr(core, "created_date_ranges", lambda: [
        core.DateRange(date(2010, 1, 1), date(2010, 1, 2)),
    ])
    monkeypatch.setattr(core.time, "sleep", lambda _: None)

    def request(url, headers):
        params = parse_qs(urlparse(url).query)
        query = params["q"][0]
        if "created:2010-01-01..2010-01-02" in query:
            begin, end = 0, total
        elif "created:2010-01-01..2010-01-01" in query:
            begin, end = 0, 750
        else:
            assert "created:2010-01-02..2010-01-02" in query
            begin, end = 750, total
        offset = (int(params["page"][0]) - 1) * 100
        return {"total_count": end - begin, "incomplete_results": False, "items": [
            {"id": number + 1, "login": f"user{number}", "html_url": f"https://github.com/user{number}"}
            for number in range(begin + offset, min(begin + offset + 100, end))
        ]}, {}

    def github_profile(username, token=None):
        profile_calls.append(username)
        return {"created_at": "2010-01-01T00:00:00Z", "name": "Test Person"}

    def telegram_page(url, headers):
        username = url.rsplit("/", 1)[-1]
        telegram_calls.append(username)
        if int(username[4:]) in matching:
            return profile_card(username)
        # A generic page or another user's card must never create a CSV row.
        return profile_card("unrelated") + f"you can contact @{username} right away"

    monkeypatch.setattr(core, "request_json_response", request)
    monkeypatch.setattr(core, "get_github_profile", github_profile)
    monkeypatch.setattr(core, "count_github_badges", lambda _: 4)
    monkeypatch.setattr(core, "request_text", telegram_page)
    output = tmp_path / "dallas.csv"
    if mode == "region":
        added = core.scrape_region(12, output, delay_seconds=0)
        contacts = core.load_contact_family(output)
        allowed_csvs = set(core.contact_shard_paths(output))
        status = json.loads((tmp_path / ".scraper-state/dallas.status.json").read_text())
        assert status["discovered_profiles"] == total
        assert status["resolved_profiles"] == total
        assert status["pending_profiles"] == 0
        assert status["validation_complete"] is True
    else:
        added = core.scrape("Dallas, TX", output, delay_seconds=0)
        contacts = core.load_contacts(output)
        allowed_csvs = {output}

    expected_names = {f"user{number}" for number in range(total)}
    assert set(profile_calls) == set(telegram_calls) == expected_names
    assert len(profile_calls) == len(telegram_calls) == total
    assert added == len(contacts) == len(matching)
    assert {contact.telegramId for contact in contacts} == {f"@user{n}" for n in matching}
    assert all(contact.telegramId == "@" + contact.link.rsplit("/", 1)[-1] for contact in contacts)
    assert set(tmp_path.rglob("*.csv")) == allowed_csvs


def test_zero_matches_does_not_export_discovered_profiles(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "REGION_STATE_DIR", tmp_path / "states")
    monkeypatch.setattr(core, "STATE_FILE", tmp_path / "legacy.json")
    monkeypatch.setattr(core, "search_github_users", lambda *a, **kw: ([{
        "username": "example", "github_url": "https://github.com/example",
    }], False))
    monkeypatch.setattr(core, "get_github_profile", lambda *a, **kw: {"created_at": "2015-01-01T00:00:00Z"})
    monkeypatch.setattr(core, "count_github_badges", lambda _: 4)
    monkeypatch.setattr(core, "request_text", lambda *a, **kw: "you can contact @example right away")
    assert core.scrape_region(12, tmp_path / "dallas.csv", delay_seconds=0) == 0
    assert not list(tmp_path.rglob("*.csv"))
