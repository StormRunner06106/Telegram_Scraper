"""Tests for bounded region CSV shards and non-fatal file locks."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from githubscraper import core
from githubscraper.ray_runner import merge_contact_files


def _contact(index: int) -> core.Contact:
    return core.Contact(
        link=f"https://github.com/user{index}",
        email=f"user{index}@example.com",
        telegramId=f"@user{index}",
        blog="",
        years=10,
        company="",
        nameMatch="matched",
    )


def test_region_store_splits_every_five_hundred_contacts(tmp_path: Path) -> None:
    base = tmp_path / "04_seattle_wa.csv"
    store = core.RegionContactCsvStore(base)

    persisted = store.append_unique([_contact(index) for index in range(1001)])

    assert len(persisted) == 1001
    assert [path.name for path in store.shard_paths] == [
        "04_seattle_wa_1.csv",
        "04_seattle_wa_2.csv",
        "04_seattle_wa_3.csv",
    ]
    assert [len(core.load_contacts(path)) for path in store.shard_paths] == [500, 500, 1]
    assert len(core.load_contact_family(base)) == 1001


def test_duplicates_across_batches_and_shards_are_not_written(tmp_path: Path) -> None:
    base = tmp_path / "region.csv"
    store = core.RegionContactCsvStore(base, shard_size=2)

    store.append_unique([_contact(0), _contact(1)])
    duplicate = _contact(1)
    case_duplicate = core.Contact(
        **{**duplicate.__dict__, "link": duplicate.link.upper()}
    )
    persisted = store.append_unique([duplicate, case_duplicate, _contact(2)])

    assert persisted == {_contact(2).link.casefold()}
    assert [len(core.load_contacts(path)) for path in store.shard_paths] == [2, 1]
    assert len(core.load_contact_family(base)) == 3


def test_locked_active_shard_rotates_without_raising(tmp_path: Path) -> None:
    base = tmp_path / "region.csv"
    store = core.RegionContactCsvStore(base, shard_size=500)
    store.append_unique([_contact(0), _contact(1)])
    locked_path = store.shard_paths[0]
    original_write = core.write_contacts

    def locked_once(path, contacts, retry_on_permission=True):
        if path == locked_path:
            raise PermissionError(5, "Access is denied", str(path))
        return original_write(path, contacts, retry_on_permission=retry_on_permission)

    with patch("githubscraper.core.write_contacts", side_effect=locked_once):
        persisted = store.append_unique([_contact(2)])

    assert persisted == {_contact(2).link.casefold()}
    assert [path.name for path in store.shard_paths] == ["region_1.csv", "region_2.csv"]
    assert [len(core.load_contacts(path)) for path in store.shard_paths] == [2, 1]
    assert len(core.load_contact_family(base)) == 3


@pytest.mark.skipif(os.name != "nt", reason="Windows file-lock behavior")
def test_real_windows_open_file_rolls_over_to_next_shard(tmp_path: Path) -> None:
    base = tmp_path / "region.csv"
    store = core.RegionContactCsvStore(base)
    store.append_unique([_contact(0)])

    with store.shard_paths[0].open("r", encoding="utf-8"):
        persisted = store.append_unique([_contact(1)])

    assert persisted == {_contact(1).link.casefold()}
    assert [path.name for path in store.shard_paths] == ["region_1.csv", "region_2.csv"]
    assert [len(core.load_contacts(path)) for path in store.shard_paths] == [1, 1]


def test_generic_csv_writer_retries_permission_errors(tmp_path: Path) -> None:
    output = tmp_path / "contacts.csv"
    original_write_once = core._write_contacts_once
    attempts = 0

    def fail_twice(path, contacts):
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise PermissionError(5, "Access is denied", str(path))
        return original_write_once(path, contacts)

    with patch("githubscraper.core._write_contacts_once", side_effect=fail_twice):
        with patch("githubscraper.core.time.sleep") as sleep:
            core.write_contacts(output, [_contact(0)])

    assert attempts == 3
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]
    assert len(core.load_contacts(output)) == 1


def test_legacy_and_failed_temp_are_migrated_without_losing_rows(tmp_path: Path) -> None:
    base = tmp_path / "04_seattle_wa.csv"
    legacy_contacts = [_contact(index) for index in range(1001)]
    core.write_contacts(base, legacy_contacts)
    failed_temp = tmp_path / ".04_seattle_wa.csv.100.200.tmp"
    core.write_contacts(failed_temp, [*legacy_contacts, _contact(1001)])

    shard_paths = core.migrate_contact_file_to_shards(base)

    assert [len(core.load_contacts(path)) for path in shard_paths] == [500, 500, 2]
    assert len(core.load_contact_family(base)) == 1002
    assert not base.exists()
    assert not failed_temp.exists()
    assert (tmp_path / "legacy" / base.name).exists()
    assert (tmp_path / "legacy" / failed_temp.name).exists()


def test_shards_are_discovered_in_numeric_order(tmp_path: Path) -> None:
    base = tmp_path / "region.csv"
    for shard_number in (10, 2, 1):
        core.write_contacts(core.contact_shard_path(base, shard_number), [])

    assert [path.name for path in core.contact_shard_paths(base)] == [
        "region_1.csv",
        "region_2.csv",
        "region_10.csv",
    ]


def test_final_merge_reads_every_shard_and_deduplicates(tmp_path: Path) -> None:
    region_base = tmp_path / "region.csv"
    destination = tmp_path / "combined.csv"
    store = core.RegionContactCsvStore(region_base, shard_size=2)
    store.append_unique([_contact(index) for index in range(5)])
    core.write_contacts(destination, [_contact(0), _contact(99)])

    merged_count = merge_contact_files([region_base], destination)

    assert merged_count == 6
    contacts = core.load_contacts(destination)
    assert len(contacts) == 6
    assert len({contact.link.casefold() for contact in contacts}) == 6
