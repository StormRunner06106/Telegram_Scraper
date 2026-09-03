"""Tests for Ray onboarding and worker-safe persistence helpers."""

from pathlib import Path
from unittest.mock import patch

from githubscraper import core
from githubscraper.agent import select_regions_for_processes
from githubscraper.ray_runner import (
    WorkerResult,
    _run_region_worker,
    merge_contact_files,
    merge_worker_outputs,
    region_output_path,
)


def _contact(username: str) -> core.Contact:
    return core.Contact(
        link=f"https://github.com/{username}",
        email=f"{username}@example.com",
        telegramId=f"@{username}",
        blog="",
        years=8,
        company="",
        nameMatch="matched",
    )


def test_country_wide_and_international_region_locations() -> None:
    canada = core.get_region_by_id(21)
    london = core.get_region_by_id(28)

    assert canada is not None
    assert london is not None
    assert core.get_region_location(canada) == "Canada"
    assert core.get_region_location(london) == "London, England, United Kingdom"
    assert core.normalize_location("United Kingdom") == "United Kingdom"


def test_process_selection_rejects_an_already_selected_location() -> None:
    regions = [
        {"id": 1, "name": "First", "country": "Canada"},
        {"id": 2, "name": "Second", "country": "United Kingdom"},
        {"id": 3, "name": "Third", "country": "United States"},
    ]
    responses = iter(["1", "1", "2"])

    with patch("githubscraper.agent.load_regions", return_value=regions):
        selected = select_regions_for_processes(2, input_fn=lambda _: next(responses))

    assert selected == [1, 2]


def test_region_state_files_are_isolated(tmp_path: Path) -> None:
    with patch.object(core, "REGION_STATE_DIR", tmp_path / "regions"):
        with patch.object(core, "STATE_FILE", tmp_path / "legacy.json"):
            core.update_region_state(21, 100, False, 100)
            core.update_region_state(27, 250, True, 250)

            assert core.get_region_state(21).index == 100
            assert core.get_region_state(27).is_end is True
            assert (tmp_path / "regions" / "region_21.json").exists()
            assert (tmp_path / "regions" / "region_27.json").exists()


def test_worker_outputs_merge_and_deduplicate(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    destination = tmp_path / "contacts.csv"
    core.write_contacts(first, [_contact("alice"), _contact("shared")])
    core.write_contacts(second, [_contact("bob"), _contact("shared")])

    merged_count = merge_contact_files([first, second], destination)

    assert merged_count == 3
    assert {contact.telegramId for contact in core.load_contacts(destination)} == {
        "@alice",
        "@bob",
        "@shared",
    }


def test_failed_worker_partial_output_is_still_merged(tmp_path: Path) -> None:
    successful = tmp_path / "successful.csv"
    failed = tmp_path / "failed.csv"
    destination = tmp_path / "contacts.csv"
    core.write_contacts(successful, [_contact("canada")])
    core.write_contacts(failed, [_contact("london")])
    results = [
        WorkerResult(21, "Canada", str(successful), 1, 1000, True),
        WorkerResult(28, "London", str(failed), 1, 650, False, "IncompleteRead"),
    ]

    merged_count = merge_worker_outputs(results, destination)

    assert merged_count == 2
    assert {contact.telegramId for contact in core.load_contacts(destination)} == {
        "@canada",
        "@london",
    }


def test_worker_output_name_is_stable() -> None:
    region = {"id": 27, "name": "United Kingdom (country-wide)"}
    assert region_output_path(region, Path("output")) == Path(
        "output/27_united_kingdom_country_wide.csv"
    )


def test_cli_defaults_to_unlimited_candidates() -> None:
    with patch("sys.argv", ["github_scraper.py", "region", "21"]):
        region_args = core.parse_args()
    with patch("sys.argv", ["github_scraper.py", "scrape", "Canada"]):
        location_args = core.parse_args()

    assert region_args.max_results is None
    assert location_args.max_results is None


def test_cli_still_allows_an_explicit_test_cap() -> None:
    with patch("sys.argv", ["github_scraper.py", "region", "21", "--max-results", "25"]):
        args = core.parse_args()

    assert args.max_results == 25


def test_each_ray_region_worker_uses_five_validation_gates(tmp_path: Path) -> None:
    output = tmp_path / "region.csv"
    region = {"id": 21, "name": "Canada", "location": "Canada"}
    state = core.RegionState(region_id=21, index=10, is_end=False, total_processed=10)

    with patch("githubscraper.ray_runner.get_region_by_id", return_value=region):
        with patch("githubscraper.ray_runner.load_contacts", return_value=[]):
            with patch("githubscraper.ray_runner.get_region_state", return_value=state):
                with patch("githubscraper.ray_runner.scrape_region", return_value=0) as scrape:
                    result = _run_region_worker(21, str(output), None, 1.0, "token")

    assert not result["error"]
    scrape.assert_called_once_with(
        region_id=21,
        output_path=output,
        max_results=None,
        delay_seconds=1.0,
        token="token",
        resume=True,
        validation_gates=core.DEFAULT_VALIDATION_GATES,
    )
