"""Regression checks for separate location outputs and the retired auto-merge."""

from dataclasses import asdict
from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest

from githubscraper import core, ray_runner, ui


def contact(username: str) -> core.Contact:
    return core.Contact(
        link=f"https://github.com/{username}",
        email="",
        telegramId=f"@{username}",
        blog="",
        years=10,
        company="",
        nameMatch="matched",
    )


def test_parallel_run_keeps_successful_and_partial_outputs_separate(tmp_path, monkeypatch):
    output = tmp_path / "new_output"
    monkeypatch.setattr(core, "OUTPUT_DIR", output)
    combined = tmp_path / "data" / "output" / "contacts.csv"
    core.write_contacts(combined, [contact("historical")])
    original = combined.read_bytes()

    def worker(region_id, output_path, *args):
        store = core.RegionContactCsvStore(Path(output_path))
        store.append_unique([contact(f"region{region_id}"), contact("shared")])
        return asdict(ray_runner.WorkerResult(
            region_id, f"Region {region_id}", output_path, 2, 10,
            region_id == 5, "" if region_id == 5 else "Interrupted worker",
        ))

    ray = MagicMock()
    ray.is_initialized.return_value = False
    ray.remote.return_value.return_value.remote.side_effect = worker
    ray.get.side_effect = lambda references: references
    monkeypatch.setitem(sys.modules, "ray", ray)
    monkeypatch.setattr(ray_runner, "merge_worker_outputs", lambda *args: pytest.fail("Automatic merge"))

    results, saved_count = ray_runner.run_parallel_scrape([5, 7])

    assert len(results) == 2
    assert saved_count == 3
    assert combined.read_bytes() == original
    assert sorted(path.name for path in output.glob("*.csv")) == [
        "05_boston_ma_1.csv", "07_chicago_il_1.csv",
    ]
    assert {row.telegramId for row in core.load_contact_family(output / "05_boston_ma.csv")} == {
        "@region5", "@shared",
    }
    assert {row.telegramId for row in core.load_contact_family(output / "07_chicago_il.csv")} == {
        "@region7", "@shared",
    }
    ray.shutdown.assert_called_once()


def test_custom_cli_saves_each_location_without_touching_contacts(tmp_path, monkeypatch):
    output = tmp_path / "new_output"
    monkeypatch.setattr(core, "OUTPUT_DIR", output)
    combined = tmp_path / "data" / "output" / "contacts.csv"
    core.write_contacts(combined, [contact("historical")])
    original = combined.read_bytes()
    monkeypatch.setattr(core, "setup_logging", lambda: tmp_path / "test.log")
    monkeypatch.setattr(core, "load_env_file", lambda: False)
    monkeypatch.setattr(core, "log_environment_status", lambda *args: None)
    monkeypatch.setattr(core, "get_github_profile", lambda *args, **kwargs: {"created_at": "2016-01-01"})
    monkeypatch.setattr(core, "github_account_age_years", lambda *args: 10)
    monkeypatch.setattr(core, "count_github_badges", lambda *args: core.MIN_GITHUB_BADGES + 1)
    monkeypatch.setattr(core, "telegram_account_exists", lambda *args: (True, "Example"))
    monkeypatch.setattr(core, "build_contact", lambda username, *args: contact(username))

    for location, username in [("Boston, MA", "boston"), ("Chicago, IL", "chicago")]:
        monkeypatch.setattr(core, "search_github_users", lambda *args, **kwargs: ([{
            "username": username, "github_url": contact(username).link,
        }], False))
        monkeypatch.setattr(core.sys, "argv", ["github_scraper.py", "scrape", location, "--delay", "0"])
        assert core.main() == 0

    assert combined.read_bytes() == original
    assert sorted(path.name for path in output.glob("*.csv")) == ["boston_ma.csv", "chicago_il.csv"]
    assert core.load_contacts(output / "boston_ma.csv") == [contact("boston")]
    assert core.load_contacts(output / "chicago_il.csv") == [contact("chicago")]


def test_csv_browser_defaults_to_new_output(monkeypatch):
    server = MagicMock()
    server.server_port = 8765
    server.serve_forever.side_effect = KeyboardInterrupt
    create_server = MagicMock(return_value=server)
    monkeypatch.setattr(ui, "create_server", create_server)

    assert ui.main(["run", "--no-browser"]) == 0
    create_server.assert_called_once_with(core.PROJECT_ROOT / "new_output", 8765)
