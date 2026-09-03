#!/usr/bin/env python3
"""Interactive onboarding for multi-location Ray scraping."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable

from githubscraper.core import (
    DEFAULT_CONTACTS_FILE,
    DEFAULT_VALIDATION_GATES,
    LOGGER,
    load_env_file,
    load_regions,
    log_environment_status,
    setup_logging,
)
from githubscraper.ray_runner import run_parallel_scrape


def show_banner() -> None:
    print("=" * 68)
    print("GitHub Location Scraper - Ray multi-process mode")
    print("One independent worker process is started for each selected location.")
    print("=" * 68)


def input_process_count(
    available_locations: int,
    input_fn: Callable[[str], str] = input,
) -> int | None:
    """Ask for the number of unique location workers before other onboarding."""
    while True:
        try:
            raw_value = input_fn(
                f"How many processes do you want to run? (1-{available_locations}, or q to quit): "
            ).strip()
        except EOFError:
            return None
        if raw_value.lower() == "q":
            return None
        try:
            process_count = int(raw_value)
        except ValueError:
            print("Enter a whole number.")
            continue
        if not 1 <= process_count <= available_locations:
            print(f"Choose a number from 1 to {available_locations}.")
            continue
        return process_count


def select_regions_for_processes(
    process_count: int,
    input_fn: Callable[[str], str] = input,
) -> list[int] | None:
    """Select a different location for each process, hiding prior choices."""
    remaining = load_regions()
    selected: list[int] = []

    for process_number in range(1, process_count + 1):
        while True:
            print(f"\nLocation for process {process_number} of {process_count}")
            print(f"{'ID':<5} {'Location':<38} {'Country':<20}")
            print("-" * 68)
            for region in remaining:
                print(
                    f"{int(region['id']):<5} "
                    f"{str(region['name']):<38} "
                    f"{str(region.get('country', 'United States')):<20}"
                )

            try:
                raw_value = input_fn("Select a location ID (or q to quit): ").strip()
            except EOFError:
                return None
            if raw_value.lower() == "q":
                return None
            try:
                region_id = int(raw_value)
            except ValueError:
                print("Enter one of the displayed location IDs.")
                continue

            chosen = next((region for region in remaining if int(region["id"]) == region_id), None)
            if chosen is None:
                print("That location is unavailable or already assigned to another process.")
                continue

            selected.append(region_id)
            remaining.remove(chosen)
            print(f"Process {process_number}: {chosen['name']}")
            break

    return selected


def _nonnegative_float_environment(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        value = float(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number.") from error
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
    return value


def main() -> int:
    load_env_file()
    log_path = setup_logging()
    log_environment_status("ray_interactive_agent")
    show_banner()
    print(f"Log file: {log_path.resolve()}")

    regions = load_regions()
    if not regions:
        print("No locations are configured.", file=sys.stderr)
        return 1

    try:
        process_count = input_process_count(len(regions))
        if process_count is None:
            return 0

        region_ids = select_regions_for_processes(process_count)
        if region_ids is None:
            return 0

        delay_seconds = _nonnegative_float_environment("SCRAPE_DELAY_SECONDS", 1.0)
        token = os.getenv("GITHUB_TOKEN") or None

        print("\nStarting Ray workers...")
        print("Candidate limit: none (processing until search partitions are exhausted)")
        print(f"Validation gates per Ray worker: {DEFAULT_VALIDATION_GATES}")
        print(f"Combined output: {DEFAULT_CONTACTS_FILE}")
        if not token:
            print("Warning: GITHUB_TOKEN is not set; GitHub permits much lower API quotas.")

        results, merged_count = run_parallel_scrape(
            region_ids=region_ids,
            delay_seconds=delay_seconds,
            token=token,
        )
    except KeyboardInterrupt:
        print("\nStopped. Each worker saves region progress as it runs.", file=sys.stderr)
        return 130
    except (RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        LOGGER.exception("Interactive Ray run failed")
        return 1

    print("\nRay worker summary")
    print("-" * 68)
    failed = False
    for result in results:
        if result.error:
            failed = True
            print(
                f"{result.region_name}: FAILED after {result.processed} users processed; "
                f"{result.added} new contacts saved - {result.error}"
            )
        else:
            status = "complete" if result.completed else "progress saved"
            print(
                f"{result.region_name}: {result.added} contacts added, "
                f"{result.processed} users processed ({status})"
            )
    print(f"Merged {merged_count} unique contacts into {DEFAULT_CONTACTS_FILE}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
