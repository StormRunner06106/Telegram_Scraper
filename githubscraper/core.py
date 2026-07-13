#!/usr/bin/env python3
"""Find GitHub users by location and keep contacts with matching Telegram usernames."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_COUNTRY = "United States"
DEFAULT_MAX_RESULTS = 1000
GITHUB_SEARCH_RESULT_LIMIT = 1000
MIN_GITHUB_BADGES = 3
MIN_GITHUB_YEARS = 6
MAX_GITHUB_YEARS = 20
GITHUB_PROFILE_URL_TEMPLATE = "https://github.com/{username}"
GITHUB_SEARCH_URL = "https://api.github.com/search/users"
GITHUB_USER_URL_TEMPLATE = "https://api.github.com/users/{username}"
TELEGRAM_URL_TEMPLATE = "https://t.me/{username}"
USER_AGENT = "GithubScraper/0.1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "output"
STATE_DIR = DATA_DIR / "state"
LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "github_scraper.txt"
DEFAULT_CONTACTS_FILE = OUTPUT_DIR / "contacts.csv"
CSV_FIELDNAMES = ["link", "email", "telegramId", "blog", "years", "company", "nameMatch"]
REGIONS_FILE = CONFIG_DIR / "regions.json"
STATE_FILE = STATE_DIR / "state.json"
SEARCH_START_YEAR = 2008
SEARCH_MAX_PARTITIONS = 5000
FOLLOWER_RANGES = [
    "followers:>=1000",
    "followers:500..999",
    "followers:100..499",
    "followers:50..99",
    "followers:10..49",
    "followers:1..9",
    "followers:0",
]

NORMAL_BIG_COMPANIES = {
    "apple", "google", "microsoft", "amazon", "meta", "facebook", "netflix", "nvidia",
    "tesla", "spacex", "twitter", "x corp", "uber", "lyft", "airbnb", "stripe",
    "salesforce", "oracle", "ibm", "intel", "amd", "qualcomm", "cisco", "adobe",
    "paypal", "square", "shopify", "spotify", "snap", "pinterest", "reddit",
    "dropbox", "slack", "zoom", "atlassian", "github", "gitlab", "docker",
    "vmware", "dell", "hp", "samsung", "sony", "tencent", "alibaba", "baidu",
    "bytedance", "tiktok", "huawei", "xiaomi", "lenovo", "asus", "acer",
}

LOGGER = logging.getLogger("githubscraper")


def setup_logging(log_path: Path | None = None) -> Path:
    """Configure the shared rotating text logger once per process."""
    path = log_path or LOG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path = path.resolve()

    for handler in LOGGER.handlers:
        if isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == resolved_path:
            return path

    handler = RotatingFileHandler(
        resolved_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(module)s.%(funcName)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    LOGGER.setLevel(logging.INFO)
    LOGGER.addHandler(handler)
    LOGGER.propagate = False
    LOGGER.info("Logger initialized path=%s", resolved_path)
    return path


def log_environment_status(source: str) -> None:
    """Log configuration readiness without writing any secret values."""
    LOGGER.info(
        "Environment status source=%s github_token_loaded=%s supabase_url_loaded=%s supabase_key_loaded=%s",
        source,
        bool(os.getenv("GITHUB_TOKEN")),
        bool(os.getenv("SUPABASE_URL")),
        bool(os.getenv("SUPABASE_KEY")),
    )


def load_env_file(path: Path | None = None) -> bool:
    """Load simple KEY=VALUE entries without overwriting exported variables."""
    env_path = path or (PROJECT_ROOT / ".env")
    if not env_path.exists():
        LOGGER.warning("Environment file not found path=%s", env_path)
        return False

    with env_path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                os.environ.setdefault(key, value)
    LOGGER.info("Environment file loaded path=%s", env_path.resolve())
    return True


@dataclass(frozen=True)
class Contact:
    link: str
    email: str
    telegramId: str
    blog: str
    years: int
    company: str
    nameMatch: str


@dataclass
class RegionState:
    region_id: int
    index: int
    is_end: bool
    total_processed: int


def load_regions() -> list[dict[str, Any]]:
    """Load configured regions."""
    regions_path = Path(REGIONS_FILE)
    if not regions_path.exists():
        return []
    
    with regions_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_region_by_id(region_id: int) -> dict[str, Any] | None:
    """Get region by ID."""
    regions = load_regions()
    for region in regions:
        if region.get("id") == region_id:
            return region
    return None


def load_state() -> list[dict[str, Any]]:
    """Load scraper progress state."""
    state_path = Path(STATE_FILE)
    if not state_path.exists():
        return []
    
    with state_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_state(states: list[dict[str, Any]]) -> None:
    """Save scraper progress state."""
    state_path = Path(STATE_FILE)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as file:
        json.dump(states, file, indent=2)


def get_region_state(region_id: int) -> RegionState:
    """Get state for a specific region."""
    states = load_state()
    for state in states:
        if state.get("region_id") == region_id:
            return RegionState(
                region_id=state.get("region_id", region_id),
                index=state.get("index", 0),
                is_end=state.get("is_end", False),
                total_processed=state.get("total_processed", 0),
            )
    
    return RegionState(region_id=region_id, index=0, is_end=False, total_processed=0)


def update_region_state(region_id: int, index: int, is_end: bool, total_processed: int) -> None:
    """Update state for a specific region."""
    states = load_state()
    
    # Find and update existing state or add new one
    found = False
    for state in states:
        if state.get("region_id") == region_id:
            state["index"] = index
            state["is_end"] = is_end
            state["total_processed"] = total_processed
            found = True
            break
    
    if not found:
        states.append({
            "region_id": region_id,
            "index": index,
            "is_end": is_end,
            "total_processed": total_processed,
        })
    
    save_state(states)
    LOGGER.info(
        "Region state saved region_id=%s index=%s total_processed=%s completed=%s",
        region_id,
        index,
        total_processed,
        is_end,
    )


def list_regions() -> None:
    """Print all available regions."""
    regions = load_regions()
    if not regions:
        print(f"No regions found in {REGIONS_FILE}")
        return
    
    print("Available regions:")
    print(f"{'ID':<5} {'Name':<30} {'State':<20}")
    print("-" * 55)
    for region in regions:
        region_id = region.get("id", "?")
        name = region.get("name", "Unknown")
        state_name = region.get("state", "Unknown")
        print(f"{region_id:<5} {name:<30} {state_name:<20}")
    
    # Show state info
    print("\nRegion progress:")
    states = load_state()
    if not states:
        print("No progress saved yet.")
    else:
        print(f"{'ID':<5} {'Index':<10} {'Processed':<12} {'Status':<10}")
        print("-" * 40)
        for state in states:
            region_id = state.get("region_id", "?")
            index = state.get("index", 0)
            total = state.get("total_processed", 0)
            status = "completed" if state.get("is_end", False) else "in progress"
            print(f"{region_id:<5} {index:<10} {total:<12} {status:<10}")


class GitHubRateLimitError(Exception):
    def __init__(
        self,
        reset_at: int | None = None,
        retry_after: int | None = None,
        resource: str | None = None,
        secondary: bool = False,
    ) -> None:
        self.reset_at = reset_at
        self.retry_after = retry_after
        self.resource = resource
        self.secondary = secondary
        super().__init__(self.message)

    @property
    def message(self) -> str:
        resource_text = f" for the {self.resource} resource" if self.resource else ""
        retry_text = ""
        if self.reset_at:
            retry_text = f" Retry after {time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(self.reset_at))}."
        elif self.retry_after:
            retry_text = f" Retry after {self.retry_after} seconds."
        limit_kind = "secondary rate limit" if self.secondary else "rate limit"
        return f"GitHub API {limit_kind} exceeded{resource_text}.{retry_text}"


def github_rate_limit_error(error: HTTPError, response_body: str = "") -> GitHubRateLimitError | None:
    """Convert GitHub primary and secondary rate responses into a retryable error."""
    if error.code not in (403, 429):
        return None

    remaining = error.headers.get("X-RateLimit-Remaining")
    retry_header = error.headers.get("Retry-After")
    response_message = response_body.lower()
    secondary = "secondary rate limit" in response_message or "abuse detection" in response_message
    is_rate_limit = error.code == 429 or remaining == "0" or retry_header is not None or secondary
    if not is_rate_limit:
        return None

    reset_header = error.headers.get("X-RateLimit-Reset")
    reset_at = int(reset_header) if reset_header and reset_header.isdigit() else None
    retry_after = int(retry_header) if retry_header and retry_header.isdigit() else None
    resource = error.headers.get("X-RateLimit-Resource")
    return GitHubRateLimitError(
        reset_at=reset_at,
        retry_after=retry_after,
        resource=resource,
        secondary=secondary,
    )


_GITHUB_RATE_GATES: dict[str, int] = {}


def github_resource_for_url(url: str) -> str | None:
    if not url.startswith("https://api.github.com/"):
        return None
    if "/search/" in url:
        return "search"
    return "core"


def github_rate_limit_wait_seconds(error: GitHubRateLimitError) -> int:
    """Return a safe wait based on GitHub's response headers."""
    if error.retry_after is not None:
        return max(1, error.retry_after)
    if error.reset_at is not None:
        return max(1, int(error.reset_at - time.time()) + 2)
    return 60


def wait_for_github_rate_gate(resource: str | None) -> None:
    if not resource:
        return
    reset_at = _GITHUB_RATE_GATES.get(resource)
    if reset_at is None:
        return
    wait_seconds = max(0, int(reset_at - time.time()) + 2)
    if wait_seconds > 0:
        print(f"GitHub {resource} quota exhausted; waiting {wait_seconds} seconds for reset...")
        LOGGER.warning("GitHub quota exhausted resource=%s wait_seconds=%s", resource, wait_seconds)
        time.sleep(wait_seconds)
    _GITHUB_RATE_GATES.pop(resource, None)


def update_github_rate_gate(headers: dict[str, str]) -> None:
    resource = headers.get("x-ratelimit-resource")
    remaining = headers.get("x-ratelimit-remaining")
    reset_header = headers.get("x-ratelimit-reset")
    if resource and remaining == "0" and reset_header and reset_header.isdigit():
        _GITHUB_RATE_GATES[resource] = int(reset_header)


def normalize_location(location: str) -> str:
    """Normalize `city, state[, country]` and default missing country."""
    parts = [part.strip() for part in location.split(",") if part.strip()]
    if len(parts) < 2:
        raise ValueError("Location must include at least city and state, like 'Austin, Texas'.")
    if len(parts) == 2:
        parts.append(DEFAULT_COUNTRY)
    return ", ".join(parts)


def request_json_response(url: str, headers: dict[str, str] | None = None) -> tuple[dict[str, Any], dict[str, str]]:
    resource = github_resource_for_url(url)
    while True:
        wait_for_github_rate_gate(resource)
        print(url)
        LOGGER.debug("GitHub API request resource=%s url=%s", resource, url)
        request = Request(url, headers=headers or {})
        try:
            with urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
                response_headers = {key.lower(): value for key, value in response.headers.items()}
                update_github_rate_gate(response_headers)
                return data, response_headers
        except HTTPError as error:
            response_body = error.read().decode("utf-8", errors="ignore")
            rate_limit_error = github_rate_limit_error(error, response_body)
            if not rate_limit_error:
                LOGGER.exception("GitHub API request failed resource=%s url=%s", resource, url)
                raise

            wait_seconds = github_rate_limit_wait_seconds(rate_limit_error)
            print(f"{rate_limit_error} Waiting {wait_seconds} seconds, then retrying...", file=sys.stderr)
            LOGGER.warning(
                "GitHub rate limit encountered resource=%s status=%s wait_seconds=%s secondary=%s",
                rate_limit_error.resource or resource,
                error.code,
                wait_seconds,
                rate_limit_error.secondary,
            )
            time.sleep(wait_seconds)


def request_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    data, _ = request_json_response(url, headers=headers)
    return data


def request_text(url: str, headers: dict[str, str] | None = None) -> str:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")


def github_headers(token: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def parse_github_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def github_account_age_years(created_at: str, now: datetime | None = None) -> int:
    created = parse_github_datetime(created_at)
    current = now or datetime.now(timezone.utc)
    years = current.year - created.year
    if (current.month, current.day) < (created.month, created.day):
        years -= 1
    return years


def account_age_is_within_required_year_range(account_age_years: int) -> bool:
    return MIN_GITHUB_YEARS <= account_age_years <= MAX_GITHUB_YEARS


def account_is_within_required_year_range(created_at: str) -> bool:
    return account_age_is_within_required_year_range(github_account_age_years(created_at))


def account_is_older_than_required_years(created_at: str) -> bool:
    """Backward-compatible alias for the current account-age range filter."""
    return account_is_within_required_year_range(created_at)


def parse_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None

    for link in link_header.split(","):
        url_part, _, rel_part = link.strip().partition(";")
        if 'rel="next"' not in rel_part:
            continue
        if url_part.startswith("<") and url_part.endswith(">"):
            return url_part[1:-1]

    return None


def count_github_badges(username: str) -> int:
    html = request_text(
        GITHUB_PROFILE_URL_TEMPLATE.format(username=username),
        headers={"User-Agent": USER_AGENT},
    )

    achievement_names = set(re.findall(r"achievement=([a-zA-Z0-9_-]+)", html))
    achievement_names.update(re.findall(r"/achievements/([a-zA-Z0-9_-]+)", html))
    return len(achievement_names)


def build_location_query(location: str) -> str:
    """Build a flexible location query that matches variations."""
    parts = [part.strip() for part in location.split(",") if part.strip()]
    
    # Use separate location: terms for each part to match variations
    # This finds "Austin, TX" and "Austin, Texas" and "Austin" etc.
    query_parts = []
    for part in parts:
        if part.lower() == "united states":
            continue
        if " " in part:
            query_parts.append(f'location:"{part}"')
        else:
            query_parts.append(f"location:{part}")
    return " ".join(query_parts)


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    @property
    def query(self) -> str:
        return f"created:{self.start.isoformat()}..{self.end.isoformat()}"

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


def search_github_users_single_query(location: str, additional_filters: str, token: str | None = None) -> tuple[list[dict[str, str]], bool]:
    """Search GitHub users with a single query.

    GitHub exposes only the first 1000 matches for any search query, so the
    boolean return value tells the caller whether this partition likely still
    has hidden results beyond the API window.
    """
    users: list[dict[str, str]] = []
    per_page = 100
    headers = github_headers(token)
    query = build_location_query(location)
    if additional_filters:
        query = f"{query} {additional_filters}"
    
    first_params = urlencode({"q": query, "per_page": per_page, "page": 1})
    first_url = f"{GITHUB_SEARCH_URL}?{first_params}"
    first_data, _ = request_json_response(first_url, headers=headers)
    total_count = int(first_data.get("total_count") or 0)
    page_count = min((total_count + per_page - 1) // per_page, GITHUB_SEARCH_RESULT_LIMIT // per_page)
    hit_search_window = total_count > GITHUB_SEARCH_RESULT_LIMIT
    LOGGER.info(
        "Search query metadata location=%s filters=%s total_count=%s accessible_pages=%s capped=%s",
        location,
        additional_filters,
        total_count,
        page_count,
        hit_search_window,
    )

    for page in range(page_count, 0, -1):
        LOGGER.info(
            "Search page focus location=%s filters=%s page=%s/%s",
            location,
            additional_filters,
            page,
            page_count,
        )
        if page == 1:
            data = first_data
        else:
            params = urlencode({"q": query, "per_page": per_page, "page": page})
            data, _ = request_json_response(f"{GITHUB_SEARCH_URL}?{params}", headers=headers)

        items = data.get("items", [])
        if not items:
            continue

        for item in items:
            username = item.get("login")
            github_url = item.get("html_url")
            if username and github_url:
                users.append({"username": username, "github_url": github_url})
                if len(users) >= GITHUB_SEARCH_RESULT_LIMIT:
                    break
        if len(users) >= GITHUB_SEARCH_RESULT_LIMIT:
            break

    return users, hit_search_window


def years_ago(current: datetime, years: int) -> date:
    current_date = current.date()
    try:
        return current_date.replace(year=current_date.year - years)
    except ValueError:
        return current_date.replace(year=current_date.year - years, day=28)


def created_date_ranges(now: datetime | None = None) -> list[DateRange]:
    """Build yearly created-date partitions for accounts in the target age range."""
    current = now or datetime.now(timezone.utc)
    oldest_allowed = years_ago(current, MAX_GITHUB_YEARS + 1) + timedelta(days=1)
    newest_allowed = years_ago(current, MIN_GITHUB_YEARS)
    search_start = max(date(SEARCH_START_YEAR, 1, 1), oldest_allowed)
    if search_start > newest_allowed:
        return []

    ranges: list[DateRange] = []

    for year in range(search_start.year, newest_allowed.year + 1):
        start = max(date(year, 1, 1), search_start)
        end = min(date(year, 12, 31), newest_allowed)
        ranges.append(DateRange(start=start, end=end))

    return ranges


def split_date_range(date_range: DateRange) -> tuple[DateRange, DateRange] | None:
    """Split a date range in half for GitHub partitions that still exceed 1000 results."""
    if date_range.days <= 1:
        return None

    midpoint = date_range.start + timedelta(days=(date_range.days // 2) - 1)
    return (
        DateRange(date_range.start, midpoint),
        DateRange(midpoint + timedelta(days=1), date_range.end),
    )


def search_github_users(location: str, max_results: int, token: str | None = None) -> tuple[list[dict[str, str]], bool]:
    """Search GitHub users by location using multiple queries to bypass 1000 limit.
    
    Uses follower count and created-date ranges to split searches and get more
    than 1000 results where GitHub's Search API allows it.
    
    Returns:
        tuple: (list of users, has_more) where has_more indicates if more results might exist
    """
    all_users: dict[str, dict[str, str]] = {}  # Use dict to deduplicate by username
    has_more = False
    initial_date_ranges = created_date_ranges()
    
    print("Fetching users from GitHub (walking last pages first and splitting crowded date ranges)...")
    LOGGER.info("Search started location=%s requested_users=%s", location, max_results)
    
    for follower_index, follower_filter in enumerate(FOLLOWER_RANGES):
        pending_ranges = list(reversed(initial_date_ranges))
        partition_count = 0

        while pending_ranges:
            date_range = pending_ranges.pop(0)
            partition_count += 1
            if partition_count > SEARCH_MAX_PARTITIONS:
                print(f"  Reached partition safety limit for {follower_filter}; moving to next follower range.")
                has_more = True
                break

            combined_filter = f"{follower_filter} {date_range.query}"
            print(f"  Searching with filter: {combined_filter}")
            LOGGER.info(
                "Search focus location=%s follower_filter=%s date_range=%s partition=%s pending=%s",
                location,
                follower_filter,
                date_range.query,
                partition_count,
                len(pending_ranges),
            )
            try:
                users, partition_has_more = search_github_users_single_query(location, combined_filter, token)
                print(f"    Found {len(users)} users")
                LOGGER.info(
                    "Search partition fetched location=%s filters=%s users=%s capped=%s",
                    location,
                    combined_filter,
                    len(users),
                    partition_has_more,
                )

                # Add to dict (deduplicates automatically)
                for user in users:
                    username = user["username"]
                    if username not in all_users:
                        all_users[username] = user
                
                if len(all_users) >= max_results:
                    print(f"Collected requested search limit of {max_results} unique users.")
                    more_partitions = bool(pending_ranges) or follower_index < len(FOLLOWER_RANGES) - 1
                    more_in_current_partition = len(all_users) > max_results
                    has_more = has_more or partition_has_more or more_partitions or more_in_current_partition
                    users_list = list(all_users.values())[:max_results]
                    return users_list, has_more

                if partition_has_more:
                    split_ranges = split_date_range(date_range)
                    if split_ranges:
                        print("    Partition is still capped by GitHub; splitting date range.")
                        right, left = split_ranges[1], split_ranges[0]
                        pending_ranges.insert(0, left)
                        pending_ranges.insert(0, right)
                        continue

                    print("    Single-day partition is still capped by GitHub; some users may remain hidden.")
                    has_more = True
                
                # Small delay between queries to be nice to GitHub
                time.sleep(0.5)

            except GitHubRateLimitError:
                # request_json_response normally waits and retries internally.
                # Preserve the error if a custom request layer raises it directly.
                raise
            except Exception as e:
                print(f"    Error with filter {combined_filter}: {e}")
                LOGGER.exception("Search partition failed location=%s filters=%s", location, combined_filter)
                continue
    
    users_list = list(all_users.values())
    print(f"Total unique users found: {len(users_list)}")
    print("Processing order is stable across resumed batches.")
    
    return users_list, has_more


def get_github_profile(username: str, token: str | None = None) -> dict[str, Any]:
    profile = request_json(
        GITHUB_USER_URL_TEMPLATE.format(username=username),
        headers=github_headers(token),
    )
    LOGGER.info("GitHub profile fetched username=%s", username)
    return profile


def normalize_name(name: str) -> str:
    """Normalize name for comparison by removing extra spaces and converting to lowercase."""
    if not name:
        return ""
    return " ".join(name.lower().strip().split())


def is_big_company(company: str | None) -> str:
    """Check if company is in the big companies list and return it, otherwise empty string."""
    if not company:
        return ""
    
    normalized = company.lower().strip()
    for big_company in NORMAL_BIG_COMPANIES:
        if big_company in normalized:
            return company
    
    return ""


def extract_telegram_full_name(username: str) -> str:
    """Extract full name from Telegram profile page."""
    try:
        html = request_text(
            TELEGRAM_URL_TEMPLATE.format(username=username),
            headers={"User-Agent": USER_AGENT},
        )
        
        # Look for <span dir="auto">Full Name</span> pattern
        match = re.search(r'<span[^>]*dir="auto"[^>]*>([^<]+)</span>', html)
        if match:
            return match.group(1).strip()
        
        # Fallback: look for tgme_page_title
        match = re.search(r'<div[^>]*class="[^"]*tgme_page_title[^"]*"[^>]*>([^<]+)</div>', html)
        if match:
            return match.group(1).strip()
        
        return ""
    except (HTTPError, URLError, TimeoutError):
        return ""


def telegram_account_exists(username: str) -> tuple[bool, str]:
    """Check if Telegram account exists and return (exists, full_name)."""
    request = Request(
        TELEGRAM_URL_TEMPLATE.format(username=username),
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urlopen(request, timeout=20) as response:
            html = response.read().decode("utf-8", errors="ignore")
            html_lower = html.lower()
            normalized_username = username.lower()
            contact_text = f"you can contact @{normalized_username} right away"
            not_found_text = "username not found"

            if response.status != 200 or not_found_text in html_lower:
                return False, ""

            exists = contact_text in html_lower or (
                "tgme_page_title" in html_lower and "tgme_username_link" in html_lower
            )
            
            if not exists:
                return False, ""
            
            # Extract full name
            match = re.search(r'<span[^>]*dir="auto"[^>]*>([^<]+)</span>', html)
            if match:
                full_name = match.group(1).strip()
                return True, full_name
            
            # Fallback: look for tgme_page_title
            match = re.search(r'<div[^>]*class="[^"]*tgme_page_title[^"]*"[^>]*>([^<]+)</div>', html)
            if match:
                full_name = match.group(1).strip()
                return True, full_name
            
            return True, ""
    except HTTPError as error:
        if error.code == 404:
            return False, ""
        raise


def load_contacts(path: Path) -> list[Contact]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        contacts = []
        for row in reader:
            if not row.get("link"):
                continue
            contacts.append(
                Contact(
                    link=row.get("link", ""),
                    email=row.get("email", ""),
                    telegramId=row.get("telegramId", ""),
                    blog=row.get("blog", ""),
                    years=int(row.get("years") or 0),
                    company=row.get("company", ""),
                    nameMatch=row.get("nameMatch", ""),
                )
            )
        return contacts


def write_contacts(path: Path, contacts: list[Contact]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for contact in contacts:
            writer.writerow(asdict(contact))


def upsert_contact(path: Path, contacts: list[Contact], contact: Contact) -> list[Contact]:
    updated_contacts = []
    replaced = False
    for existing_contact in contacts:
        if existing_contact.link.lower() == contact.link.lower():
            updated_contacts.append(contact)
            replaced = True
        else:
            updated_contacts.append(existing_contact)

    if not replaced:
        updated_contacts.append(contact)

    write_contacts(path, updated_contacts)
    return updated_contacts


def build_contact(
    username: str,
    account_age_years: int,
    github_url: str,
    profile: dict[str, Any],
    telegram_full_name: str,
) -> Contact:
    github_name = str(profile.get("name") or "")
    company = is_big_company(profile.get("company"))
    
    # Compare names
    github_normalized = normalize_name(github_name)
    telegram_normalized = normalize_name(telegram_full_name)
    
    if github_normalized and telegram_normalized:
        name_match = "matched" if github_normalized == telegram_normalized else "not matched"
    else:
        name_match = "unknown"
    
    return Contact(
        link=github_url,
        email=str(profile.get("email") or ""),
        telegramId=f"@{username}",
        blog=str(profile.get("blog") or ""),
        years=account_age_years,
        company=company,
        nameMatch=name_match,
    )


def scrape(location: str, output_path: Path, max_results: int, delay_seconds: float, token: str | None) -> int:
    normalized_location = normalize_location(location)
    print(f"Searching GitHub users in: {normalized_location}")
    LOGGER.info(
        "Custom scrape started location=%s max_results=%s output=%s authenticated=%s",
        normalized_location,
        max_results,
        output_path,
        bool(token),
    )

    contacts = load_contacts(output_path)
    seen_links = {contact.link.lower() for contact in contacts}

    try:
        github_users, _ = search_github_users(normalized_location, max_results=max_results, token=token)
    except GitHubRateLimitError as error:
        print(error, file=sys.stderr)
        return 0

    print(f"Found {len(github_users)} GitHub users. Checking account age, badges, and Telegram usernames...")

    added = 0
    processed = 0
    for user in github_users:
        # Stop if we've processed enough users to fill the CSV
        if processed >= max_results:
            break
            
        username = user["username"]
        github_url = user["github_url"]
        LOGGER.info("Profile processing focus username=%s processed=%s/%s", username, processed, max_results)
        if github_url.lower() in seen_links:
            print(f"Skipping duplicate: {username}")
            continue

        try:
            profile = get_github_profile(username, token=token)
        except GitHubRateLimitError as error:
            print(error, file=sys.stderr)
            print("Stopping early and saving contacts found so far.", file=sys.stderr)
            break
        except (HTTPError, URLError, TimeoutError) as error:
            print(f"Could not fetch GitHub profile for {username}: {error}", file=sys.stderr)
            LOGGER.exception("GitHub profile fetch failed username=%s", username)
            continue

        created_at = str(profile.get("created_at") or "")
        if not created_at:
            print(f"Skipped without GitHub created date: {username}")
            continue

        account_age_years = github_account_age_years(created_at)
        if not account_age_is_within_required_year_range(account_age_years):
            print(
                f"Skipped account age outside {MIN_GITHUB_YEARS}-{MAX_GITHUB_YEARS} years: "
                f"{username} ({account_age_years} years)"
            )
            continue

        try:
            badge_count = count_github_badges(username)
        except (HTTPError, URLError, TimeoutError) as error:
            print(f"Could not check GitHub badges for {username}: {error}", file=sys.stderr)
            LOGGER.exception("GitHub badge fetch failed username=%s", username)
            continue

        if badge_count <= MIN_GITHUB_BADGES:
            print(f"Skipped badge count <= {MIN_GITHUB_BADGES}: {username} ({badge_count} badges)")
            continue

        try:
            exists, telegram_full_name = telegram_account_exists(username)
        except (HTTPError, URLError, TimeoutError) as error:
            print(f"Could not check Telegram for {username}: {error}", file=sys.stderr)
            LOGGER.exception("Telegram profile fetch failed username=%s", username)
            exists = False
            telegram_full_name = ""

        if exists:
            contact = build_contact(username, account_age_years, github_url, profile, telegram_full_name)
            contacts = upsert_contact(output_path, contacts, contact)
            seen_links.add(github_url.lower())
            added += 1
            
            company_info = f", company: {contact.company}" if contact.company else ""
            name_info = f", name: {contact.nameMatch}"
            print(f"Upserted lead: {username} ({account_age_years} years, {badge_count} badges{company_info}{name_info})")
            LOGGER.info("Lead saved username=%s output=%s", username, output_path)
        else:
            print(f"Skipped without Telegram match: {username}")
            LOGGER.info("Profile rejected username=%s reason=no_telegram_match", username)
        
        processed += 1

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    print(f"Upserted {added} leads to {output_path}")
    LOGGER.info("Custom scrape finished location=%s processed=%s leads_added=%s", normalized_location, processed, added)
    return added


def scrape_region(
    region_id: int,
    output_path: Path,
    max_results: int,
    delay_seconds: float,
    token: str | None,
    resume: bool = True,
) -> int:
    """Scrape a region by ID with resume capability."""
    region = get_region_by_id(region_id)
    if not region:
        print(f"Region ID {region_id} not found in {REGIONS_FILE}", file=sys.stderr)
        return 0
    
    city = region.get("city", "")
    state = region.get("state", "")
    location = f"{city}, {state}"
    
    print(f"Scraping region {region_id}: {region.get('name', location)}")
    LOGGER.info(
        "Region scrape started region_id=%s location=%s max_results=%s output=%s resume=%s authenticated=%s",
        region_id,
        location,
        max_results,
        output_path,
        resume,
        bool(token),
    )
    
    # Load state
    state_obj = get_region_state(region_id)
    
    if state_obj.is_end and resume and max_results <= state_obj.index:
        print(f"Region {region_id} already completed. Use --no-resume to restart.")
        return 0
    if state_obj.is_end and resume and max_results > state_obj.index:
        print(
            f"Region {region_id} was previously marked complete at index {state_obj.index}, "
            f"but the requested limit is {max_results}. Reopening from the reversed fetched list."
        )
    
    start_index = state_obj.index if resume else 0
    total_processed = state_obj.total_processed if resume else 0
    
    if start_index > 0:
        print(f"Resuming from index {start_index} (already processed {total_processed} users)")
    
    normalized_location = normalize_location(location)
    contacts = load_contacts(output_path)
    seen_links = {contact.link.lower() for contact in contacts}

    # A resumed batch must rebuild a stable prefix through the saved index and
    # then collect the next requested batch. Searching for max_results alone
    # would return the same prefix forever once start_index reached that size.
    search_target = start_index + max_results
    LOGGER.info(
        "Region search target region_id=%s saved_index=%s batch_limit=%s search_target=%s",
        region_id,
        start_index,
        max_results,
        search_target,
    )
    try:
        github_users, has_more = search_github_users(
            normalized_location,
            max_results=search_target,
            token=token,
        )
    except GitHubRateLimitError as error:
        print(error, file=sys.stderr)
        return 0

    print(f"Found {len(github_users)} GitHub users total.")
    if has_more:
        print(
            f"Note: GitHub may still have more users in this region. "
            f"Collected {len(github_users)} unique users (GitHub caps each search query at "
            f"{GITHUB_SEARCH_RESULT_LIMIT} results; the scraper works around that with partitions)."
        )
    
    # Skip to start_index
    users_to_process = github_users[start_index:]
    print(f"Processing {len(users_to_process)} users (skipping first {start_index})...")

    added = 0
    current_index = start_index
    users_checked = 0  # Track how many users we've actually checked (not skipped)
    
    try:
        for user in users_to_process:
            # Stop if we've checked enough users to meet the limit
            if users_checked >= max_results:
                print(f"Reached limit of {max_results} users to check. Stopping.")
                break
                
            username = user["username"]
            github_url = user["github_url"]
            LOGGER.info(
                "Profile processing focus region_id=%s username=%s index=%s batch_checked=%s/%s",
                region_id,
                username,
                current_index,
                users_checked,
                max_results,
            )
            
            if github_url.lower() in seen_links:
                print(f"Skipping duplicate: {username}")
                current_index += 1
                total_processed += 1
                continue

            try:
                profile = get_github_profile(username, token=token)
            except GitHubRateLimitError as error:
                print(error, file=sys.stderr)
                print("Stopping early and saving progress.", file=sys.stderr)
                update_region_state(region_id, current_index, False, total_processed)
                break
            except (HTTPError, URLError, TimeoutError) as error:
                print(f"Could not fetch GitHub profile for {username}: {error}", file=sys.stderr)
                LOGGER.exception("GitHub profile fetch failed region_id=%s username=%s", region_id, username)
                current_index += 1
                total_processed += 1
                users_checked += 1
                continue

            created_at = str(profile.get("created_at") or "")
            if not created_at:
                print(f"Skipped without GitHub created date: {username}")
                current_index += 1
                total_processed += 1
                users_checked += 1
                continue

            account_age_years = github_account_age_years(created_at)
            if not account_age_is_within_required_year_range(account_age_years):
                print(
                    f"Skipped account age outside {MIN_GITHUB_YEARS}-{MAX_GITHUB_YEARS} years: "
                    f"{username} ({account_age_years} years)"
                )
                current_index += 1
                total_processed += 1
                users_checked += 1
                continue

            try:
                badge_count = count_github_badges(username)
            except (HTTPError, URLError, TimeoutError) as error:
                print(f"Could not check GitHub badges for {username}: {error}", file=sys.stderr)
                LOGGER.exception("GitHub badge fetch failed region_id=%s username=%s", region_id, username)
                current_index += 1
                total_processed += 1
                users_checked += 1
                continue

            if badge_count <= MIN_GITHUB_BADGES:
                print(f"Skipped badge count <= {MIN_GITHUB_BADGES}: {username} ({badge_count} badges)")
                current_index += 1
                total_processed += 1
                users_checked += 1
                continue

            try:
                exists, telegram_full_name = telegram_account_exists(username)
            except (HTTPError, URLError, TimeoutError) as error:
                print(f"Could not check Telegram for {username}: {error}", file=sys.stderr)
                LOGGER.exception("Telegram profile fetch failed region_id=%s username=%s", region_id, username)
                exists = False
                telegram_full_name = ""

            if exists:
                contact = build_contact(username, account_age_years, github_url, profile, telegram_full_name)
                contacts = upsert_contact(output_path, contacts, contact)
                seen_links.add(github_url.lower())
                added += 1
                
                company_info = f", company: {contact.company}" if contact.company else ""
                name_info = f", name: {contact.nameMatch}"
                print(f"Upserted lead: {username} ({account_age_years} years, {badge_count} badges{company_info}{name_info})")
                LOGGER.info("Lead saved region_id=%s username=%s output=%s", region_id, username, output_path)
            else:
                print(f"Skipped without Telegram match: {username}")
                LOGGER.info("Profile rejected region_id=%s username=%s reason=no_telegram_match", region_id, username)

            current_index += 1
            total_processed += 1
            users_checked += 1
            
            # Save progress every 10 users
            if total_processed % 10 == 0:
                update_region_state(region_id, current_index, False, total_processed)
            
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        
        # Determine if we've truly exhausted all available users
        # is_end should be True only if:
        # 1. We've processed all users from GitHub's search results AND
        # 2. GitHub has no more users (has_more is False) OR we hit the user check limit
        reached_check_limit = users_checked >= max_results
        processed_all_github_users = current_index >= len(github_users)
        
        # is_end is True only when we've exhausted GitHub's results (not just our limit)
        is_complete = processed_all_github_users and not has_more
        
        update_region_state(region_id, current_index, is_complete, total_processed)
        
        if is_complete:
            print(f"Region {region_id} completed! All available GitHub users have been processed.")
        elif reached_check_limit:
            print(f"Reached check limit of {max_results} users. Region not marked as complete.")
        else:
            visible_remaining = max(0, len(github_users) - current_index)
            print(f"Progress saved. {visible_remaining} users currently available after the saved index.")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user. Saving progress...")
        update_region_state(region_id, current_index, False, total_processed)
        raise

    print(f"Upserted {added} leads to {output_path}")
    print(f"Total processed: {total_processed} users")
    LOGGER.info(
        "Region scrape batch finished region_id=%s current_index=%s total_processed=%s leads_added=%s",
        region_id,
        current_index,
        total_processed,
        added,
    )
    return added


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find GitHub users by location and save users with matching Telegram accounts."
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List regions command
    list_parser = subparsers.add_parser("list", help="List all available regions")
    
    # Scrape by location command
    location_parser = subparsers.add_parser("scrape", help="Scrape by location string")
    location_parser.add_argument(
        "location",
        help="Location as 'city, state[, country]'. Country defaults to United States.",
    )
    location_parser.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_CONTACTS_FILE),
        help=f"CSV output file path. Defaults to {DEFAULT_CONTACTS_FILE}.",
    )
    location_parser.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=(
            f"Maximum GitHub users to check. Defaults to {DEFAULT_MAX_RESULTS}; "
            f"GitHub Search exposes up to {GITHUB_SEARCH_RESULT_LIMIT} results per query."
        ),
    )
    location_parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between Telegram checks. Defaults to 1.0.",
    )
    location_parser.add_argument(
        "--github-token",
        default=os.getenv("GITHUB_TOKEN"),
        help="Optional GitHub token. Defaults to the GITHUB_TOKEN environment variable.",
    )
    
    # Scrape by region ID command
    region_parser = subparsers.add_parser("region", help="Scrape by region ID with resume support")
    region_parser.add_argument(
        "region_id",
        type=int,
        help=f"Region ID from {REGIONS_FILE}",
    )
    region_parser.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_CONTACTS_FILE),
        help=f"CSV output file path. Defaults to {DEFAULT_CONTACTS_FILE}.",
    )
    region_parser.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=(
            f"Maximum GitHub users to check. Defaults to {DEFAULT_MAX_RESULTS}; "
            f"GitHub Search exposes up to {GITHUB_SEARCH_RESULT_LIMIT} results per query."
        ),
    )
    region_parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between Telegram checks. Defaults to 1.0.",
    )
    region_parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Start from beginning instead of resuming from saved state.",
    )
    region_parser.add_argument(
        "--github-token",
        default=os.getenv("GITHUB_TOKEN"),
        help="Optional GitHub token. Defaults to the GITHUB_TOKEN environment variable.",
    )
    
    return parser.parse_args()


def main() -> int:
    log_path = setup_logging()
    env_loaded = load_env_file()
    log_environment_status("github_scraper_cli")
    LOGGER.info("CLI started env_file_loaded=%s arguments=%s", env_loaded, sys.argv[1:])
    print(f"Log file: {log_path.resolve()}")
    args = parse_args()
    
    # Handle list command
    if args.command == "list":
        list_regions()
        return 0
    
    # Handle region command
    if args.command == "region":
        if args.max_results < 1:
            print("--max-results must be greater than 0", file=sys.stderr)
            return 2
        if args.delay < 0:
            print("--delay must be 0 or greater", file=sys.stderr)
            return 2
        
        try:
            scrape_region(
                region_id=args.region_id,
                output_path=Path(args.output),
                max_results=args.max_results,
                delay_seconds=args.delay,
                token=args.github_token,
                resume=not args.no_resume,
            )
        except ValueError as error:
            print(error, file=sys.stderr)
            LOGGER.exception("Invalid region command input")
            return 2
        except GitHubRateLimitError as error:
            print(error, file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\nStopped by user.", file=sys.stderr)
            LOGGER.warning("Region command interrupted by user")
            return 130
        except (HTTPError, URLError, TimeoutError) as error:
            print(f"Request failed: {error}", file=sys.stderr)
            LOGGER.exception("Region command request failed")
            return 1
        
        return 0
    
    # Handle scrape command (or default for backward compatibility)
    if args.command == "scrape" or args.command is None:
        if not hasattr(args, "location"):
            print("Error: Please specify a command: 'list', 'scrape', or 'region'", file=sys.stderr)
            print("Run with --help for usage information.", file=sys.stderr)
            return 2
        
        if args.max_results < 1:
            print("--max-results must be greater than 0", file=sys.stderr)
            return 2
        if args.delay < 0:
            print("--delay must be 0 or greater", file=sys.stderr)
            return 2
        if not args.github_token and args.max_results > DEFAULT_MAX_RESULTS:
            print(
                "Warning: unauthenticated GitHub API calls are limited. "
                "Use GITHUB_TOKEN or --github-token for larger runs.",
                file=sys.stderr,
            )

        try:
            scrape(
                location=args.location,
                output_path=Path(args.output),
                max_results=args.max_results,
                delay_seconds=args.delay,
                token=args.github_token,
            )
        except ValueError as error:
            print(error, file=sys.stderr)
            LOGGER.exception("Invalid custom scrape command input")
            return 2
        except GitHubRateLimitError as error:
            print(error, file=sys.stderr)
            return 1
        except (HTTPError, URLError, TimeoutError) as error:
            print(f"Request failed: {error}", file=sys.stderr)
            LOGGER.exception("Custom scrape command request failed")
            return 1

        return 0
    
    print(f"Unknown command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
