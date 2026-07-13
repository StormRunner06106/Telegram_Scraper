"""Regression tests for GitHub primary and secondary rate-limit handling."""

import io
import json
from email.message import Message
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
            {"GITHUB_TOKEN": "do-not-log-this-token", "SUPABASE_URL": "configured"},
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
    assert "supabase_url_loaded=True" in contents
    assert "supabase_key_loaded=False" in contents
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
