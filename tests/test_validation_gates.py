"""Concurrency and persistence tests for per-region validation gates."""

from __future__ import annotations

import threading
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from githubscraper import core


REGION = {
    "id": 21,
    "name": "Canada",
    "location": "Canada",
    "country": "Canada",
}
EMPTY_STATE = core.RegionState(region_id=21, index=0, is_end=False, total_processed=0)


def _users(count: int) -> list[dict[str, str]]:
    return [
        {
            "username": f"user{index}",
            "github_url": f"https://github.com/user{index}",
        }
        for index in range(count)
    ]


def _contact(username: str, github_url: str | None = None) -> core.Contact:
    return core.Contact(
        link=github_url or f"https://github.com/{username}",
        email=f"{username}@example.com",
        telegramId=f"@{username}",
        blog="",
        years=10,
        company="",
        nameMatch="matched",
    )


def _accepted_outcome(
    index: int,
    gate_id: int,
    user: dict[str, str],
) -> core.ValidationOutcome:
    username = user["username"]
    return core.ValidationOutcome(
        index=index,
        gate_id=gate_id,
        username=username,
        github_url=user["github_url"],
        contact=_contact(username, user["github_url"]),
        message=f"Qualified lead: {username}",
    )


def test_region_runs_five_validation_gates_and_checks_each_user_once(tmp_path: Path) -> None:
    users = _users(8)
    first_wave = {user["username"] for user in users[:5]}
    barrier = threading.Barrier(5)
    lock = threading.Lock()
    active = 0
    peak_active = 0
    profile_calls: Counter[str] = Counter()
    worker_threads: set[str] = set()

    def fake_profile(username: str, token: str | None = None) -> dict[str, str]:
        nonlocal active, peak_active
        with lock:
            profile_calls[username] += 1
            active += 1
            peak_active = max(peak_active, active)
            worker_threads.add(threading.current_thread().name)
        try:
            if username in first_wave:
                barrier.wait(timeout=3)
            return {
                "created_at": "2015-01-01T00:00:00Z",
                "name": username,
            }
        finally:
            with lock:
                active -= 1

    output = tmp_path / "contacts.csv"
    with patch("githubscraper.core.get_region_by_id", return_value=REGION):
        with patch("githubscraper.core.get_region_state", return_value=EMPTY_STATE):
            with patch("githubscraper.core.search_github_users", return_value=(users, False)):
                with patch("githubscraper.core.get_github_profile", side_effect=fake_profile):
                    with patch("githubscraper.core.count_github_badges", return_value=4):
                        with patch(
                            "githubscraper.core.telegram_account_exists",
                            return_value=(True, "Test User"),
                        ):
                            with patch("githubscraper.core.update_region_state") as update_state:
                                added = core.scrape_region(
                                    region_id=21,
                                    output_path=output,
                                    delay_seconds=0,
                                    token="token",
                                    resume=True,
                                )

    contacts = core.load_contacts(output)
    assert added == len(users)
    assert peak_active == core.DEFAULT_VALIDATION_GATES
    assert len(worker_threads) == core.DEFAULT_VALIDATION_GATES
    assert profile_calls == Counter(user["username"] for user in users)
    assert len(contacts) == len(users)
    assert len({contact.link.casefold() for contact in contacts}) == len(users)
    update_state.assert_called_with(21, len(users), True, len(users))


def test_duplicate_and_existing_links_are_never_dispatched_to_two_gates(
    tmp_path: Path,
) -> None:
    output = tmp_path / "contacts.csv"
    core.write_contacts(output, [_contact("existing")])
    users = [
        {"username": "existing", "github_url": "https://github.com/EXISTING"},
        {"username": "duplicate", "github_url": "https://github.com/duplicate"},
        {"username": "DUPLICATE", "github_url": "https://github.com/DUPLICATE"},
        {"username": "unique", "github_url": "https://github.com/unique"},
    ]
    assignments: list[tuple[int, str]] = []
    lock = threading.Lock()

    def fake_validate(index, gate_id, user, region_id, delay_seconds, token):
        with lock:
            assignments.append((index, user["username"]))
        return _accepted_outcome(index, gate_id, user)

    with patch("githubscraper.core.get_region_by_id", return_value=REGION):
        with patch("githubscraper.core.get_region_state", return_value=EMPTY_STATE):
            with patch("githubscraper.core.search_github_users", return_value=(users, False)):
                with patch("githubscraper.core.validate_user_in_gate", side_effect=fake_validate):
                    with patch("githubscraper.core.update_region_state") as update_state:
                        added = core.scrape_region(
                            region_id=21,
                            output_path=output,
                            delay_seconds=0,
                            resume=True,
                        )

    assert sorted(assignments) == [(1, "duplicate"), (3, "unique")]
    assert added == 2
    contacts = core.load_contacts(output)
    assert len(contacts) == 3
    assert len({contact.link.casefold() for contact in contacts}) == 3
    update_state.assert_called_with(21, 4, True, 4)


def test_max_results_is_global_across_all_gates(tmp_path: Path) -> None:
    users = _users(20)
    assignments: list[int] = []
    lock = threading.Lock()

    def fake_validate(index, gate_id, user, region_id, delay_seconds, token):
        with lock:
            assignments.append(index)
        return core.ValidationOutcome(
            index=index,
            gate_id=gate_id,
            username=user["username"],
            github_url=user["github_url"],
            contact=None,
            message="rejected",
        )

    with patch("githubscraper.core.get_region_by_id", return_value=REGION):
        with patch("githubscraper.core.get_region_state", return_value=EMPTY_STATE):
            with patch("githubscraper.core.search_github_users", return_value=(users, True)):
                with patch("githubscraper.core.validate_user_in_gate", side_effect=fake_validate):
                    with patch("githubscraper.core.update_region_state") as update_state:
                        core.scrape_region(
                            region_id=21,
                            output_path=tmp_path / "contacts.csv",
                            max_results=7,
                            delay_seconds=0,
                            resume=True,
                        )

    assert sorted(assignments) == list(range(7))
    update_state.assert_called_with(21, 7, False, 7)


def test_resumed_run_assigns_only_users_after_saved_frontier(tmp_path: Path) -> None:
    users = _users(10)
    resumed_state = core.RegionState(region_id=21, index=4, is_end=False, total_processed=4)
    assignments: list[int] = []
    search_targets: list[int | None] = []

    def fake_search(location: str, max_results: int | None, token=None):
        search_targets.append(max_results)
        return users, True

    def fake_validate(index, gate_id, user, region_id, delay_seconds, token):
        assignments.append(index)
        return core.ValidationOutcome(
            index=index,
            gate_id=gate_id,
            username=user["username"],
            github_url=user["github_url"],
            contact=None,
            message="rejected",
        )

    with patch("githubscraper.core.get_region_by_id", return_value=REGION):
        with patch("githubscraper.core.get_region_state", return_value=resumed_state):
            with patch("githubscraper.core.search_github_users", side_effect=fake_search):
                with patch("githubscraper.core.validate_user_in_gate", side_effect=fake_validate):
                    with patch("githubscraper.core.update_region_state") as update_state:
                        core.scrape_region(
                            region_id=21,
                            output_path=tmp_path / "contacts.csv",
                            max_results=3,
                            delay_seconds=0,
                            resume=True,
                        )

    assert search_targets == [7]
    assert sorted(assignments) == [4, 5, 6]
    update_state.assert_called_with(21, 7, False, 7)


def test_resume_checkpoint_never_crosses_an_unfinished_gate(tmp_path: Path) -> None:
    users = _users(5)
    release_first = threading.Event()
    later_rows_persisted = threading.Event()
    state_updates: list[tuple[int, int, bool, int]] = []
    run_errors: list[BaseException] = []
    output = tmp_path / "contacts.csv"
    original_write_contacts = core.write_contacts

    def fake_validate(index, gate_id, user, region_id, delay_seconds, token):
        if index == 0 and not release_first.wait(timeout=5):
            raise TimeoutError("test did not release the first gate")
        return _accepted_outcome(index, gate_id, user)

    def recording_write(path: Path, contacts: list[core.Contact]) -> None:
        original_write_contacts(path, contacts)
        if len(contacts) >= 4:
            later_rows_persisted.set()

    def run_scrape() -> None:
        try:
            core.scrape_region(
                region_id=21,
                output_path=output,
                delay_seconds=0,
                resume=True,
            )
        except BaseException as error:
            run_errors.append(error)

    with patch("githubscraper.core.get_region_by_id", return_value=REGION):
        with patch("githubscraper.core.get_region_state", return_value=EMPTY_STATE):
            with patch("githubscraper.core.search_github_users", return_value=(users, False)):
                with patch("githubscraper.core.validate_user_in_gate", side_effect=fake_validate):
                    with patch("githubscraper.core.write_contacts", side_effect=recording_write):
                        with patch(
                            "githubscraper.core.update_region_state",
                            side_effect=lambda *args: state_updates.append(args),
                        ):
                            scraper_thread = threading.Thread(target=run_scrape)
                            scraper_thread.start()
                            assert later_rows_persisted.wait(timeout=3)

                            # Indices 1-4 are saved, but index 0 is still running.
                            # The resume cursor must therefore remain at zero.
                            assert not state_updates

                            release_first.set()
                            scraper_thread.join(timeout=5)

    assert not scraper_thread.is_alive()
    assert not run_errors
    assert state_updates[-1] == (21, 5, True, 5)
    contacts = core.load_contacts(output)
    assert len(contacts) == 5
    assert len({contact.link.casefold() for contact in contacts}) == 5
