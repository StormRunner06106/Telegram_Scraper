"""Ray orchestration for independent, location-based scraper workers."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from githubscraper.core import (
    DEFAULT_CONTACTS_FILE,
    OUTPUT_DIR,
    get_region_by_id,
    get_region_state,
    load_contacts,
    scrape_region,
    write_contacts,
)


@dataclass(frozen=True)
class WorkerResult:
    region_id: int
    region_name: str
    output_path: str
    added: int
    processed: int
    completed: bool
    error: str = ""


def region_output_path(region: dict[str, Any], output_dir: Path | None = None) -> Path:
    """Build a stable output path for one region worker."""
    destination = output_dir or OUTPUT_DIR / "regions"
    slug = re.sub(r"[^a-z0-9]+", "_", str(region.get("name") or "region").lower()).strip("_")
    return destination / f"{int(region['id']):02d}_{slug}.csv"


def merge_contact_files(paths: Iterable[Path], destination: Path = DEFAULT_CONTACTS_FILE) -> int:
    """Merge worker CSVs into one deduplicated contact file."""
    contacts_by_link = {contact.link.lower(): contact for contact in load_contacts(destination)}
    for path in paths:
        for contact in load_contacts(path):
            contacts_by_link[contact.link.lower()] = contact

    contacts = list(contacts_by_link.values())
    write_contacts(destination, contacts)
    return len(contacts)


def merge_worker_outputs(
    results: Iterable[WorkerResult],
    destination: Path = DEFAULT_CONTACTS_FILE,
) -> int:
    """Merge saved output even when a worker reports a recoverable failure."""
    return merge_contact_files((Path(result.output_path) for result in results), destination)


def _run_region_worker(
    region_id: int,
    output_path: str,
    max_results: int | None,
    delay_seconds: float,
    token: str | None,
) -> dict[str, Any]:
    """Execute one region inside a Ray worker process."""
    region = get_region_by_id(region_id)
    region_name = str(region.get("name")) if region else f"Region {region_id}"
    starting_links = {contact.link.lower() for contact in load_contacts(Path(output_path))}
    try:
        added = scrape_region(
            region_id=region_id,
            output_path=Path(output_path),
            max_results=max_results,
            delay_seconds=delay_seconds,
            token=token,
            resume=True,
        )
        state = get_region_state(region_id)
        result = WorkerResult(
            region_id=region_id,
            region_name=region_name,
            output_path=output_path,
            added=added,
            processed=state.total_processed,
            completed=state.is_end,
        )
    except Exception as error:  # Ray must return other workers' results if one location fails.
        current_links = {contact.link.lower() for contact in load_contacts(Path(output_path))}
        result = WorkerResult(
            region_id=region_id,
            region_name=region_name,
            output_path=output_path,
            added=len(current_links - starting_links),
            processed=get_region_state(region_id).total_processed,
            completed=False,
            error=f"{type(error).__name__}: {error}",
        )
    return asdict(result)


def run_parallel_scrape(
    region_ids: list[int],
    max_results: int | None = None,
    delay_seconds: float = 1.0,
    token: str | None = None,
    destination: Path = DEFAULT_CONTACTS_FILE,
) -> tuple[list[WorkerResult], int]:
    """Run one Ray process per unique region and merge all saved outputs."""
    if not region_ids:
        raise ValueError("Select at least one region.")
    if len(region_ids) != len(set(region_ids)):
        raise ValueError("Each Ray process must use a different region.")
    if max_results is not None and max_results < 1:
        raise ValueError("max_results must be at least 1.")
    if delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative.")

    regions = [get_region_by_id(region_id) for region_id in region_ids]
    if any(region is None for region in regions):
        raise ValueError("One or more selected region IDs do not exist.")

    try:
        import ray
    except ImportError as error:
        raise RuntimeError("Ray is not installed. Run: pip install -r requirements.txt") from error

    started_here = not ray.is_initialized()
    if started_here:
        ray.init(
            num_cpus=len(region_ids),
            include_dashboard=False,
            log_to_driver=True,
        )

    remote_worker = ray.remote(num_cpus=1, max_retries=0)(_run_region_worker)
    references = []
    for region in regions:
        assert region is not None
        output_path = region_output_path(region)
        references.append(
            remote_worker.remote(
                int(region["id"]),
                str(output_path),
                max_results,
                delay_seconds,
                token,
            )
        )

    try:
        payloads = ray.get(references)
    except KeyboardInterrupt:
        for reference in references:
            ray.cancel(reference, force=True)
        raise
    finally:
        if started_here:
            ray.shutdown()

    results = [WorkerResult(**payload) for payload in payloads]
    merged_count = merge_worker_outputs(results, destination)
    return results, merged_count
