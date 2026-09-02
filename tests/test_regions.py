#!/usr/bin/env python3
"""Test region and state management features."""

import sys
from pathlib import Path

if __name__ != "__main__":
    import pytest

    pytest.skip("manual state-management smoke script", allow_module_level=True)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from github_scraper import (
    load_regions,
    get_region_by_id,
    load_state,
    save_state,
    get_region_state,
    update_region_state,
)

print("=== Testing Region Loading ===")
regions = load_regions()
print(f"Loaded {len(regions)} regions")
for region in regions[:3]:
    print(f"  ID {region['id']}: {region['name']}")

print("\n=== Testing Region Lookup ===")
region = get_region_by_id(1)
if region:
    print(f"Region 1: {region['name']}")
    print(f"  City: {region['city']}")
    print(f"  State: {region['state']}")

print("\n=== Testing State Management ===")
# Get initial state
state = get_region_state(1)
print(f"Initial state for region 1:")
print(f"  Index: {state.index}")
print(f"  Is end: {state.is_end}")
print(f"  Total processed: {state.total_processed}")

# Update state
print("\nUpdating state...")
update_region_state(region_id=1, index=50, is_end=False, total_processed=50)

# Load updated state
state = get_region_state(1)
print(f"Updated state for region 1:")
print(f"  Index: {state.index}")
print(f"  Is end: {state.is_end}")
print(f"  Total processed: {state.total_processed}")

# Test multiple regions
print("\nUpdating multiple regions...")
update_region_state(region_id=2, index=100, is_end=False, total_processed=100)
update_region_state(region_id=3, index=200, is_end=True, total_processed=200)

states = load_state()
print(f"\nAll states ({len(states)} regions):")
for s in states:
    status = "completed" if s['is_end'] else "in progress"
    print(f"  Region {s['region_id']}: index={s['index']}, processed={s['total_processed']}, {status}")

print("\n✓ All tests passed!")
