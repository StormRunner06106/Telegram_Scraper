"""Shared, atomic CSV access for the scraper and local browser UI."""

from __future__ import annotations

import csv
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path


def read_flag(value: object) -> bool:
    return str(value).strip().casefold() in {"true", "1", "yes", "checked"}


@contextmanager
def csv_lock(path: Path, timeout: float = 5.0):
    """Coordinate read/modify/replace across UI requests and scraper processes.

    Lock a stable sibling file: locking the CSV itself would prevent atomic
    replacement on Windows and would lock an obsolete inode on POSIX.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(f".{path.name}.lock").open("a+b") as lock:
        lock.seek(0, os.SEEK_END)
        if lock.tell() == 0:
            lock.write(b"\0")
            lock.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                lock.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise PermissionError(f"CSV is busy: {path.name}") from None
                time.sleep(0.05)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]], bool]:
    """Read without coercing values or losing user-added columns."""
    with path.open("rb") as stream:
        has_bom = stream.read(3) == b"\xef\xbb\xbf"
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        fields = reader.fieldnames or []
        if len(set(fields)) != len(fields) or any(not name for name in fields):
            raise ValueError("CSV headers must be nonempty and unique.")
        rows = list(reader)
        if any(None in row or None in row.values() for row in rows):
            raise ValueError("CSV rows must have the same number of fields as the header.")
    return fields, rows, has_bom


def write_csv(path: Path, fields: list[str], rows, has_bom: bool = False) -> None:
    """Replace a CSV atomically; callers hold csv_lock for read/modify/write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8-sig" if has_bom else "utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
