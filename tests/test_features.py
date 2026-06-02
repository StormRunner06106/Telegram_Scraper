#!/usr/bin/env python3
"""Test the new features: company filtering and name matching."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from github_scraper import (
    is_big_company,
    normalize_name,
    extract_telegram_full_name,
    telegram_account_exists,
)

# Test company filtering
print("=== Testing Company Filtering ===")
test_companies = [
    "Apple Inc.",
    "Google",
    "@NVIDIA",
    "Meta",
    "Some Random Startup",
    "Microsoft Corporation",
    None,
    "",
]

for company in test_companies:
    result = is_big_company(company)
    print(f"{str(company):30} -> '{result}'")

# Test name normalization
print("\n=== Testing Name Normalization ===")
test_names = [
    ("Brian Takita", "brian takita"),
    ("John  Doe", "john doe"),
    ("JANE SMITH", "jane smith"),
    ("", ""),
]

for name1, name2 in test_names:
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    match = "matched" if norm1 == norm2 else "not matched"
    print(f"'{name1}' vs '{name2}' -> {match}")

# Test Telegram name extraction (using a known account)
print("\n=== Testing Telegram Name Extraction ===")
test_usernames = ["getify"]  # Known Telegram user

for username in test_usernames:
    try:
        exists, full_name = telegram_account_exists(username)
        print(f"@{username}: exists={exists}, name='{full_name}'")
    except Exception as e:
        print(f"@{username}: Error - {e}")
