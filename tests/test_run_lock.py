"""Regression checks for competing region workers and OS lock recovery."""

import errno
import json
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from githubscraper import core, csv_storage, ray_runner
from githubscraper.progress import ValidationJournal, validation_policy


def _hold_region_lock(output, ready, release):
    """Separate process matching the lock held by an ongoing CLI scan."""
    output = Path(output)
    with csv_storage.csv_lock(output.parent / ".scraper-state" / f"{output.stem}.run"):
        ready.set()
        if not release.wait(30):
            raise RuntimeError("Test did not release the region owner")


@pytest.fixture
def locked_region(tmp_path):
    output = tmp_path / "12_dallas_tx.csv"
    context = multiprocessing.get_context("spawn")
    ready, release = context.Event(), context.Event()
    owner = context.Process(target=_hold_region_lock, args=(str(output), ready, release))
    owner.start()
    try:
        assert ready.wait(10), "The test owner did not acquire its run lock"
        yield output, owner, release
    finally:
        # Terminating a process inside Event.wait can leave the Event's
        # internal condition locked. Do not signal an owner already exited.
        if owner.is_alive():
            release.set()
        owner.join(timeout=5)
        if owner.is_alive():
            owner.terminate()
            owner.join(timeout=5)
        owner.close()


def _prepare_region(output, monkeypatch):
    monkeypatch.setattr(core, "REGION_STATE_DIR", output.parent / "states")
    monkeypatch.setattr(core, "STATE_FILE", output.parent / "legacy.json")
    monkeypatch.setattr(ray_runner, "setup_logging", lambda *args: None)
    users = [{"username": name, "github_url": f"https://github.com/{name}"}
             for name in ("checked", "pending")]
    policy = validation_policy(core.build_location_query("Dallas, TX"),
                               core.MIN_GITHUB_YEARS, core.MAX_GITHUB_YEARS, core.MIN_GITHUB_BADGES)
    journal = ValidationJournal(output, policy)
    journal.save_candidates(users, False)
    journal.record([core.ValidationOutcome(
        0, 1, "checked", users[0]["github_url"], None, "No match", reason="no_telegram",
    )], users)
    journal.write_status({
        "stage": "validating", "resolved_profiles": 1, "discovered_profiles": 2,
        "pending_profiles": 1, "saved_contacts": 0, "validation_complete": False,
    })
    journal.close()
    calls = []

    def validate(index, gate, user, *args):
        calls.append(user["username"])
        contact = core.Contact(user["github_url"], "", "@" + user["username"], "", 10, "", "matched")
        return core.ValidationOutcome(index, gate, user["username"], user["github_url"],
                                      contact, "Qualified", reason="qualified")

    def unexpected_search(*args, **kwargs):
        raise AssertionError("The pending journal should be resumed before another search")

    monkeypatch.setattr(core, "validate_user_in_gate", validate)
    monkeypatch.setattr(core, "search_github_users", unexpected_search)
    return calls


def test_ray_worker_waits_past_old_timeout_then_resumes_journal(locked_region, monkeypatch, capsys):
    output, owner, release = locked_region
    calls = _prepare_region(output, monkeypatch)
    status_path = output.parent / ".scraper-state" / f"{output.stem}.status.json"
    journal_path = status_path.with_name(f"{output.stem}.sqlite3")
    before = status_path.read_bytes(), journal_path.read_bytes()
    waiting = Event()
    original_info = core.LOGGER.info

    def log(message, *args, **kwargs):
        if "another process holds the region run lock" in message:
            waiting.set()
        original_info(message, *args, **kwargs)

    monkeypatch.setattr(core.LOGGER, "info", log)
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(ray_runner._run_region_worker, 12, str(output), None, 0, None)
        try:
            assert waiting.wait(5), "Waiting must be visible immediately"
            # Real elapsed time and real cross-process OS locking: the old
            # implementation returned a FAILED result after five seconds.
            with pytest.raises(TimeoutError):
                result.result(timeout=5.2)
            assert calls == []
            assert not list(output.parent.glob("*.csv"))
            assert (status_path.read_bytes(), journal_path.read_bytes()) == before
            # Independent outputs remain available during this wait.
            with csv_storage.csv_lock(output.parent / ".scraper-state" / "other.run", timeout=0):
                pass
        finally:
            release.set()
        payload = result.result(timeout=10)

    assert payload["error"] == ""
    assert payload["completed"] is True
    assert payload["added"] == 1
    assert calls == ["pending"]
    assert [contact.telegramId for contact in core.load_contact_family(output)] == ["@pending"]
    status = json.loads(status_path.read_text())
    assert status["resolved_profiles"] == 2
    assert status["pending_profiles"] == 0
    text = capsys.readouterr().out
    assert "1/2 profiles resolved, 1 pending, 0 saved contacts" in text
    assert "run lock acquired; reloading saved progress" in text


def test_owner_exit_releases_lock_without_deleting_lock_file(locked_region, monkeypatch):
    output, owner, _ = locked_region
    calls = _prepare_region(output, monkeypatch)
    # Simulate an abrupt owner exit; its persistent lock file remains on disk.
    owner.terminate()
    owner.join(timeout=5)
    assert not owner.is_alive()
    lock_path = output.parent / ".scraper-state" / f".{output.stem}.run.lock"
    assert lock_path.exists()
    result = ray_runner._run_region_worker(12, str(output), None, 0, None)
    assert result["error"] == ""
    assert result["completed"] is True
    assert calls == ["pending"]
    assert lock_path.exists()


@pytest.mark.parametrize("status_content", [None, "not json", "[]"])
def test_wait_is_interruptible_without_modifying_owner_state(locked_region, monkeypatch, status_content):
    output, _, _ = locked_region
    status_path = output.parent / ".scraper-state" / f"{output.stem}.status.json"
    if status_content is not None:
        status_path.write_text(status_content)

    def interrupt(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(csv_storage, "time", SimpleNamespace(monotonic=lambda: 0, sleep=interrupt))
    with pytest.raises(KeyboardInterrupt):
        core.scrape_region(12, output, resume=False)
    assert not status_path.with_name(f"{output.stem}.sqlite3").exists()
    assert not list(output.parent.glob("*.csv"))
    if status_content is None:
        assert not status_path.exists()
    else:
        assert status_path.read_text() == status_content


def test_wait_reports_progress_periodically_without_timing_out(locked_region, monkeypatch):
    output, _, _ = locked_region
    elapsed = [0]
    reports = []

    def sleep(_):
        elapsed[0] += 1
        if elapsed[0] > 61:
            raise KeyboardInterrupt

    monkeypatch.setattr(csv_storage, "time", SimpleNamespace(monotonic=lambda: elapsed[0], sleep=sleep))
    with pytest.raises(KeyboardInterrupt):
        with csv_storage.csv_lock(
            output.parent / ".scraper-state" / f"{output.stem}.run",
            timeout=None, on_wait=lambda: reports.append(elapsed[0]),
        ):
            pytest.fail("A waiting process acquired the owner's lock")
    assert reports == [0, 30, 60]


def test_non_contention_os_errors_are_not_retried(tmp_path, monkeypatch):
    def broken_lock(*args):
        raise OSError(errno.EBADF, "Bad descriptor")

    if os.name == "nt":
        import msvcrt
        monkeypatch.setattr(msvcrt, "locking", broken_lock)
    else:
        import fcntl
        monkeypatch.setattr(fcntl, "flock", broken_lock)

    with pytest.raises(OSError) as failure:
        with csv_storage.csv_lock(tmp_path / "region.run", timeout=None):
            pytest.fail("Invalid lock acquired")
    assert failure.value.errno == errno.EBADF
