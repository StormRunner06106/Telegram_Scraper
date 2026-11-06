"""CSV UI persistence, writer integration, and local HTTP boundaries."""

from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

import gscraper
from githubscraper import core, ui
from githubscraper.csv_storage import csv_lock, read_csv, write_csv
from githubscraper.ray_runner import merge_contact_files


def contact(number: int = 0, is_read: bool = False) -> core.Contact:
    return core.Contact(f"https://example.com/{number}", "hello@example.com", "@hello", "", 10, "A company", "matched", is_read)


@pytest.fixture
def library(tmp_path):
    return ui.CsvLibrary(tmp_path)


def test_legacy_migration_and_manual_toggles_preserve_every_value(library):
    path = library.root / "legacy.csv"
    original = {"link": "https://example.com/a", "notes": 'Hello, "world"\n日本語', "years": "0010", "company": "<script>alert(1)</script>"}
    write_csv(path, list(original), [original], has_bom=True)
    table = library.table(path.name)
    assert table["fields"] == [*original, "is_read"]
    assert table["rows"][0]["is_read"] is False
    for value in (True, False):
        row = table["rows"][0]
        library.set_read(path.name, row["index"], row["key"], value)
        fields, rows, bom = read_csv(path)
        assert bom is True
        assert rows == [{**original, "is_read": str(value).lower()}]
        assert fields == table["fields"]


def test_stale_row_is_rejected_without_overwriting_new_content(library):
    path = library.root / "contacts.csv"
    core.write_contacts(path, [contact(1), contact(2)])
    row = library.table(path.name)["rows"][0]
    core.write_contacts(path, [contact(2), contact(1), contact(3)])
    before = path.read_bytes()
    with pytest.raises(ui.RowChangedError):
        library.set_read(path.name, 0, row["key"], True)
    assert path.read_bytes() == before


def test_cached_scraper_shard_keeps_read_and_unread_ui_edits(library):
    store = core.RegionContactCsvStore(library.root / "region.csv")
    store.append_unique([contact(1, True)])
    path = store.shard_paths[0]
    row = library.table(path.name)["rows"][0]
    library.set_read(path.name, 0, row["key"], False)
    store.append_unique([contact(2)])
    assert core.load_contacts(path)[0].is_read is False
    library.set_read(path.name, 0, row["key"], True)
    store.append_unique([contact(3)])
    assert core.load_contacts(path)[0].is_read is True
    assert len(core.load_contacts(path)) == 3


def test_merge_retains_destination_flags_and_imports_new_flags(library):
    destination = library.root / "combined.csv"
    source = library.root / "source.csv"
    core.write_contacts(destination, [contact(1, True), contact(2, False)])
    core.write_contacts(source, [contact(1, False), contact(2, True), contact(3, True)])
    merge_contact_files([source], destination)
    assert [row.is_read for row in core.load_contacts(destination)] == [True, False, True]


def test_writer_preserves_custom_columns_and_legacy_read_default(library):
    path = library.root / "contacts.csv"
    row = {"link": contact().link, "years": "10", "notes": "keep me"}
    write_csv(path, list(row), [row])
    assert core.load_contacts(path)[0].is_read is False
    core.write_contacts(path, [contact(), contact(1)])
    fields, rows, _ = read_csv(path)
    assert "notes" in fields
    assert rows[0]["notes"] == "keep me"
    assert rows[1]["notes"] == ""
    assert all(row["is_read"] == "false" for row in rows)


def test_parallel_edits_do_not_lose_other_row_changes(library):
    path = library.root / "contacts.csv"
    core.write_contacts(path, [contact(index) for index in range(12)])
    rows = library.table(path.name)["rows"]
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda row: library.set_read(path.name, row["index"], row["key"], True), rows))
    assert all(row.is_read for row in core.load_contacts(path))


def test_failed_replace_leaves_original_and_cleans_temp(library, monkeypatch):
    path = library.root / "contacts.csv"
    core.write_contacts(path, [contact()])
    row = library.table(path.name)["rows"][0]
    before = path.read_bytes()
    def deny_replace(*args):
        raise PermissionError("locked")
    monkeypatch.setattr(Path, "replace", deny_replace)
    with pytest.raises(PermissionError):
        library.set_read(path.name, 0, row["key"], True)
    assert path.read_bytes() == before
    assert not list(library.root.glob("*.tmp"))


@pytest.mark.parametrize("content", ["link,link\na,b\n", "link,notes\na,b,c\n", "link,notes\na\n", 'link,notes\na,"unterminated'])
def test_malformed_csv_is_not_rewritten(library, content):
    path = library.root / "bad.csv"
    path.write_text(content, encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises((ValueError, csv.Error)):
        library.table(path.name)
    assert path.read_bytes() == before


def test_file_discovery_and_path_boundaries(library, tmp_path):
    nested = tmp_path / "regions" / "a.CSV"
    write_csv(nested, ["link"], [])
    (tmp_path / "secret.txt").write_text("not a CSV")
    assert [file["name"] for file in library.list_files()] == ["regions/a.CSV"]
    for invalid in ("../outside.csv", str(nested.resolve()), "secret.txt", "", None):
        with pytest.raises(ValueError):
            library.table(invalid)


def test_busy_lock_times_out_without_modifying_file(library):
    path = library.root / "contacts.csv"
    core.write_contacts(path, [contact()])
    before = path.read_bytes()
    with csv_lock(path):
        with pytest.raises(PermissionError):
            with csv_lock(path, timeout=0.05):
                pytest.fail("A second writer acquired the same lock")
    assert path.read_bytes() == before


@pytest.fixture
def live_server(tmp_path):
    server = ui.create_server(tmp_path, port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", tmp_path
    server.shutdown()
    server.server_close()
    thread.join()


def test_http_api_assets_and_origin_checks(live_server):
    url, root = live_server
    core.write_contacts(root / "contacts.csv", [contact()])
    headers = {"X-GScraper-UI": "1"}
    for asset in ("/", "/state.js", "/app.js", "/styles.css"):
        with urlopen(url + asset) as response:
            assert response.status == 200
            assert response.headers["X-Content-Type-Options"] == "nosniff"
    with urlopen(Request(url + "/api/table?name=contacts.csv", headers=headers)) as response:
        row = json.load(response)["rows"][0]
    payload = json.dumps({"name": "contacts.csv", "index": 0, "key": row["key"], "is_read": True}).encode()
    with urlopen(Request(url + "/api/read", data=payload, headers={**headers, "Content-Type": "application/json"})) as response:
        assert json.load(response)["is_read"] is True
    assert core.load_contacts(root / "contacts.csv")[0].is_read is True
    invalid = [
        (Request(url + "/api/files"), 403),
        (Request(url + "/api/files", headers={**headers, "Origin": "https://other.example"}), 403),
        (Request(url + "/api/files", headers={**headers, "Host": "other.example"}), 403),
        (Request(url + "/api/table?name=../secret.csv", headers=headers), 400),
        (Request(url + "/.env"), 404),
        (Request(url + "/api/read", data=b'[]', headers={**headers, "Content-Type": "application/json"}), 400),
        (Request(url + "/api/read", data=payload, headers={"Content-Type": "application/json"}), 403),
    ]
    for request, status in invalid:
        with pytest.raises(HTTPError) as failure:
            urlopen(request)
        assert failure.value.code == status


def test_ui_entrypoint_bypasses_scraper_and_tmux(monkeypatch):
    monkeypatch.setattr(gscraper.sys, "argv", ["gscraper", "ui", "run", "--no-browser"])
    monkeypatch.setattr(gscraper, "run_in_tmux_if_needed", lambda: pytest.fail("UI launched tmux"))
    monkeypatch.setattr(gscraper, "main", lambda: pytest.fail("UI launched scraper"))
    calls = []
    monkeypatch.setattr(ui, "main", lambda args: calls.append(args) or 0)
    assert gscraper.entrypoint() == 0
    assert calls == [["run", "--no-browser"]]


@pytest.mark.parametrize("no_browser", [True, False])
def test_ui_run_opens_browser_unless_disabled(tmp_path, monkeypatch, no_browser):
    opened = []
    monkeypatch.setattr(ui.webbrowser, "open", lambda url: opened.append(url))
    def stop(server):
        raise KeyboardInterrupt
    monkeypatch.setattr(ui.ThreadingHTTPServer, "serve_forever", stop)
    args = ["run", "--port", "0", "--directory", str(tmp_path)]
    if no_browser:
        args.append("--no-browser")
    assert ui.main(args) == 0
    assert len(opened) == (0 if no_browser else 1)
    if opened:
        assert opened[0].startswith("http://127.0.0.1:")
