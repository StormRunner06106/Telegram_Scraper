# GitHub Scraper

Find GitHub users by location, filter older accounts with GitHub achievements, verify matching Telegram usernames, and save qualified contacts to CSV.

## Quick Start

```bash
python check_env.py
python github_scraper.py list
python github_scraper.py region 1 --max-results 100
```

Interactive agent mode is still available:

```bash
python gscraper.py
```

## Project Layout

```text
githubscraper/        Python package with scraper and agent code
config/               Static configuration, including regions.json
data/output/          Generated CSV/JSON output
data/state/           Local scraper progress state
docs/                 Historical setup notes and guides
tests/                Smoke tests and exploratory test scripts
github_scraper.py     Backward-compatible CLI entrypoint
gscraper.py           Backward-compatible interactive entrypoint
setup_supabase.py     Supabase setup and sync helper
check_env.py          Environment checker
```

## Configuration

Create `.env` from `.env.example` and set:

```env
GITHUB_TOKEN=your_github_token_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

`GITHUB_TOKEN` is optional for small runs, but strongly recommended for GitHub API rate limits. Supabase is optional and only needed for remote state sync.

## Output And State

Default CLI output goes to:

```text
data/output/contacts.csv
```

Local resume state is stored at:

```text
data/state/state.json
```

Both generated folders are ignored by git.

## Tests

Most tests are smoke scripts:

```bash
python tests/test_setup.py
python tests/test_regions.py
python tests/test_features.py
```

`tests/test_search.py` performs live GitHub API calls and requires `GITHUB_TOKEN`.
