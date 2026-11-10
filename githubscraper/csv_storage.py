"""Shared, atomic CSV access for the scraper and local browser UI."""

from __future__ import annotations

import csv
import errno
import os
import tempfile
import time
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path


def read_flag(value: object) -> bool:
    return str(value).strip().casefold() in {"true", "1", "yes", "checked"}


@contextmanager
def csv_lock(
    path: Path,
    timeout: float | None = 5.0,
    *,
    on_wait: Callable[[], None] | None = None,
):
    """Coordinate read/modify/replace across UI requests and scraper processes.

    Lock a stable sibling file: locking the CSV itself would prevent atomic
    replacement on Windows and would lock an obsolete inode on POSIX.
    A run lasting hours uses timeout=None; UI writes keep the short timeout.
    on_wait reports contention immediately and every 30 seconds thereafter.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(f".{path.name}.lock").open("a+b") as lock:
        lock.seek(0, os.SEEK_END)
        if lock.tell() == 0:
            lock.write(b"\0")
            lock.flush()
        deadline = None if timeout is None else time.monotonic() + timeout
        next_wait_report = None
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
            except OSError as error:
                # Only lock contention is retryable. Bad handles, unsupported
                # locking, and other OS failures must keep their real cause.
                if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                now = time.monotonic()
                if deadline is not None and now >= deadline:
                    raise PermissionError(f"CSV is busy: {path.name}") from None
                if on_wait is not None and (next_wait_report is None or now >= next_wait_report):
                    on_wait()
                    next_wait_report = now + 30
                time.sleep(0.5 if timeout is None else 0.05)
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
