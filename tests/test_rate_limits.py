"""Regression tests for GitHub primary and secondary rate-limit handling."""

import io
import json
from email.message import Message
from http.client import IncompleteRead
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from githubscraper import core


class FakeResponse:
    def __init__(self, data: dict, headers: dict[str, str] | None = None) -> None:
        self._body = json.dumps(data).encode("utf-8")
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return self._body


class FakeTextResponse(FakeResponse):
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")
        self.headers = {}


class BrokenReadResponse(FakeTextResponse):
    def read(self) -> bytes:
        raise IncompleteRead(b"", 100)


def rate_error(
    status: int,
    body: str,
    *,
    remaining: str = "0",
    retry_after: str | None = None,
    resource: str = "search",
) -> HTTPError:
    headers = Message()
    headers["X-RateLimit-Remaining"] = remaining
    headers["X-RateLimit-Resource"] = resource
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(
        "https://api.github.com/search/users",
        status,
        "rate limited",
        headers,
        io.BytesIO(body.encode("utf-8")),
    )


def test_request_retries_same_search_after_429() -> None:
    error = rate_error(429, '{"message":"rate limit exceeded"}', retry_after="7")
    response = FakeResponse(
        {"total_count": 1, "items": []},
        {
            "X-RateLimit-Resource": "search",
            "X-RateLimit-Remaining": "29",
            "X-RateLimit-Reset": "9999999999",
        },
    )

    core._GITHUB_RATE_GATES.clear()
    with patch("githubscraper.core.urlopen", side_effect=[error, response]) as mocked_open:
        with patch("githubscraper.core.time.sleep") as mocked_sleep:
            data, headers = core.request_json_response("https://api.github.com/search/users?q=test")

    assert mocked_open.call_count == 2
    mocked_sleep.assert_called_once_with(7)
    assert data["total_count"] == 1
    assert headers["x-ratelimit-resource"] == "search"


def test_secondary_403_retries_even_when_primary_quota_remains() -> None:
    error = rate_error(
        403,
        '{"message":"You have exceeded a secondary rate limit"}',
        remaining="21",
    )
    response = FakeResponse({}, {"X-RateLimit-Resource": "search", "X-RateLimit-Remaining": "20"})

    core._GITHUB_RATE_GATES.clear()
    with patch("githubscraper.core.urlopen", side_effect=[error, response]):
        with patch("githubscraper.core.time.sleep") as mocked_sleep:
            core.request_json_response("https://api.github.com/search/users?q=test")

    mocked_sleep.assert_called_once_with(60)


def test_json_request_retries_incomplete_response_body() -> None:
    response = FakeResponse({"login": "octocat"})

    with patch("githubscraper.core.urlopen", side_effect=[BrokenReadResponse(""), response]) as mocked_open:
        with patch("githubscraper.core.time.sleep") as mocked_sleep:
            data, _ = core.request_json_response("https://api.github.com/users/octocat")

    assert data["login"] == "octocat"
    assert mocked_open.call_count == 2
    mocked_sleep.assert_called_once_with(2)


def test_text_request_retries_incomplete_response_body() -> None:
    response = FakeTextResponse("complete response")

    with patch("githubscraper.core.urlopen", side_effect=[BrokenReadResponse(""), response]) as mocked_open:
        with patch("githubscraper.core.time.sleep") as mocked_sleep:
            body = core.request_text("https://github.com/octocat")

    assert body == "complete response"
    assert mocked_open.call_count == 2
    mocked_sleep.assert_called_once_with(2)


def test_interrupted_http_error_body_retries_original_request() -> None:
    error = rate_error(429, '{"message":"rate limit exceeded"}', retry_after="7")
    error.read = lambda: (_ for _ in ()).throw(IncompleteRead(b"", 50))
    response = FakeResponse({"login": "octocat"})

    with patch("githubscraper.core.urlopen", side_effect=[error, response]) as mocked_open:
        with patch("githubscraper.core.time.sleep") as mocked_sleep:
            data, _ = core.request_json_response("https://api.github.com/users/octocat")

    assert data["login"] == "octocat"
    assert mocked_open.call_count == 2
    mocked_sleep.assert_called_once_with(2)


def test_telegram_lookup_uses_retrying_text_request() -> None:
    html = (
        '<div class="tgme_page_title">Octo Cat</div>'
        '<a class="tgme_username_link">You can contact @octocat right away</a>'
    )
    with patch("githubscraper.core.request_text", return_value=html) as mocked_request:
        exists, full_name = core.telegram_account_exists("octocat")

    assert exists is True
    assert full_name == "Octo Cat"
    mocked_request.assert_called_once()


def test_search_and_profile_urls_use_independent_resources() -> None:
    assert core.github_resource_for_url("https://api.github.com/search/users?q=test") == "search"
    assert core.github_resource_for_url("https://api.github.com/users/octocat") == "core"


def test_env_loader_does_not_overwrite_exported_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING=value-from-file\nNEW_KEY=new-value\n", encoding="utf-8")

    with patch.dict(core.os.environ, {"EXISTING": "exported-value"}, clear=True):
        core.load_env_file(env_file)
        assert core.os.environ["EXISTING"] == "exported-value"
        assert core.os.environ["NEW_KEY"] == "new-value"


def test_text_logger_records_environment_readiness_without_secret_values(tmp_path: Path) -> None:
    log_path = tmp_path / "scraper.txt"
    existing_handlers = set(core.LOGGER.handlers)

    try:
        core.setup_logging(log_path)
        with patch.dict(
            core.os.environ,
            {"GITHUB_TOKEN": "do-not-log-this-token"},
            clear=True,
        ):
            core.log_environment_status("test")
        with patch("githubscraper.core.request_json", return_value={"login": "octocat"}):
            core.get_github_profile("octocat", token="do-not-log-this-token")

        for handler in core.LOGGER.handlers:
            handler.flush()
        contents = log_path.read_text(encoding="utf-8")
    finally:
        for handler in list(core.LOGGER.handlers):
            if handler not in existing_handlers:
                core.LOGGER.removeHandler(handler)
                handler.close()

    assert "github_token_loaded=True" in contents
    assert "GitHub profile fetched username=octocat" in contents
    assert "do-not-log-this-token" not in contents


def test_resumed_region_searches_through_saved_index_plus_next_batch(tmp_path: Path) -> None:
    observed_targets: list[int] = []

    def fake_search(location: str, max_results: int, token=None):
        observed_targets.append(max_results)
        return [], True

    state = core.RegionState(region_id=5, index=250, is_end=False, total_processed=250)
    region = {"id": 5, "name": "Boston, MA", "city": "Boston", "state": "Massachusetts"}

    with patch("githubscraper.core.get_region_by_id", return_value=region):
        with patch("githubscraper.core.get_region_state", return_value=state):
            with patch("githubscraper.core.load_contacts", return_value=[]):
                with patch("githubscraper.core.search_github_users", side_effect=fake_search):
                    with patch("githubscraper.core.update_region_state"):
                        core.scrape_region(
                            region_id=5,
                            output_path=tmp_path / "contacts.csv",
                            max_results=100,
                            delay_seconds=0,
                            token="token",
                            resume=True,
                        )

    assert observed_targets == [350]


def test_unlimited_resumed_region_requests_all_search_results(tmp_path: Path) -> None:
    observed_targets: list[int | None] = []

    def fake_search(location: str, max_results: int | None, token=None):
        observed_targets.append(max_results)
        return [], True

    state = core.RegionState(region_id=21, index=1000, is_end=False, total_processed=1000)
    region = {"id": 21, "name": "Canada", "location": "Canada", "country": "Canada"}

    with patch("githubscraper.core.get_region_by_id", return_value=region):
        with patch("githubscraper.core.get_region_state", return_value=state):
            with patch("githubscraper.core.load_contacts", return_value=[]):
                with patch("githubscraper.core.search_github_users", side_effect=fake_search):
                    with patch("githubscraper.core.update_region_state"):
                        core.scrape_region(
                            region_id=21,
                            output_path=tmp_path / "contacts.csv",
                            max_results=None,
                            delay_seconds=0,
                            token="token",
                            resume=True,
                        )

    assert observed_targets == [None]


def test_completed_region_is_not_reopened_for_unlimited_run(tmp_path: Path) -> None:
    state = core.RegionState(region_id=21, index=5000, is_end=True, total_processed=5000)
    region = {"id": 21, "name": "Canada", "location": "Canada", "country": "Canada"}

    with patch("githubscraper.core.get_region_by_id", return_value=region):
        with patch("githubscraper.core.get_region_state", return_value=state):
            with patch("githubscraper.core.search_github_users") as mocked_search:
                added = core.scrape_region(
                    region_id=21,
                    output_path=tmp_path / "contacts.csv",
                    max_results=None,
                    delay_seconds=0,
                    token="token",
                    resume=True,
                )

    assert added == 0
    mocked_search.assert_not_called()


def test_unlimited_region_checks_every_returned_candidate_and_completes(tmp_path: Path) -> None:
    region = {"id": 21, "name": "Canada", "location": "Canada", "country": "Canada"}
    state = core.RegionState(region_id=21, index=0, is_end=False, total_processed=0)
    users = [
        {"username": f"user{index}", "github_url": f"https://github.com/user{index}"}
        for index in range(3)
    ]
    profile = {"created_at": "2015-01-01T00:00:00Z"}

    with patch("githubscraper.core.get_region_by_id", return_value=region):
        with patch("githubscraper.core.get_region_state", return_value=state):
            with patch("githubscraper.core.load_contacts", return_value=[]):
                with patch("githubscraper.core.search_github_users", return_value=(users, False)):
                    with patch("githubscraper.core.get_github_profile", return_value=profile) as profiles:
                        with patch("githubscraper.core.count_github_badges", return_value=4):
                            with patch("githubscraper.core.telegram_account_exists", return_value=(False, "")):
                                with patch("githubscraper.core.update_region_state") as update_state:
                                    core.scrape_region(
                                        region_id=21,
                                        output_path=tmp_path / "contacts.csv",
                                        max_results=None,
                                        delay_seconds=0,
                                        token="token",
                                        resume=True,
                                    )

    assert profiles.call_count == 3
    update_state.assert_called_with(21, 3, True, 3)
