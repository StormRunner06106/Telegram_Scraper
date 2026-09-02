# GitHub Location Scraper

Collect public GitHub profiles by location, validate the existing account-age,
achievement, and matching Telegram criteria, and save contacts to CSV. The
interactive runner uses Ray to process several unique locations concurrently.

## Setup

Python 3.10 or newer is required.

```bash
python -m pip install -r requirements.txt
copy .env.example .env
python check_env.py
```

Set `GITHUB_TOKEN` in `.env`. Authenticated requests have substantially higher
GitHub API quotas than anonymous requests.

## Interactive Ray runner

```bash
python gscraper.py
```

On Linux and macOS, an interactive run automatically opens or attaches to a
`tmux` session named `gscraper`. Detach without stopping the workers by pressing
`Ctrl-b`, then `d`, and reconnect later with:

```bash
tmux attach -t gscraper
```

Install `tmux` before the first run. To intentionally run in the current
terminal instead, use `GSCRAPER_NO_TMUX=1 python gscraper.py`. Windows runs in
the current terminal because native `tmux` is unavailable.

On startup the runner:

1. Asks how many processes to run.
2. Shows the full location list for process 1.
3. Removes that selection before showing the list for process 2, and repeats.
4. Starts one Ray worker per selected location.
5. Writes an independent CSV and resume-state file per worker.
6. Merges every worker CSV, including partial output from an interrupted worker,
   into `data/output/contacts.csv`.

Canada and the United Kingdom can be selected country-wide. Toronto, Vancouver,
Montreal, Ottawa, Calgary, London, Manchester, Edinburgh, Bristol, and Cambridge
are also available alongside the existing U.S. cities.

There is no application-level candidate limit. Each process continues until all
supported search partitions for its location have been enumerated and checked.
Configure the delay between profile checks in `.env` when needed:

```env
SCRAPE_DELAY_SECONDS=1.0
```

Progress is resumable, so another run continues each selected region from its
saved index.

## Direct CLI

```bash
python github_scraper.py list
python github_scraper.py region 21
python github_scraper.py scrape "United Kingdom"
```

`--max-results N` remains available only when you intentionally want a short
manual test run. Omitting it performs the unlimited run.

## Data locations

- `data/output/contacts.csv`: deduplicated combined contacts
- `data/output/regions/*.csv`: worker-specific contacts
- `data/state/regions/*.json`: independent worker resume state
- `data/logs/github_scraper.txt`: runtime log

## API behavior

The scraper only queries public endpoints and honors GitHub rate-limit responses,
including primary and secondary limits. Interrupted responses are retried with
backoff. GitHub Search exposes at most 1,000 results for a single query; the
scraper enumerates supported follower and account-date partitions to collect
additional public results where available. "Unlimited" means there is no local
candidate-count cutoff; it cannot expose private profiles or results that GitHub
does not return through its API.

## Tests

```bash
python -m pytest -q
```

`tests/test_search.py` is a live smoke script and requires `GITHUB_TOKEN` when
run directly.
