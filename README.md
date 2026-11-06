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
5. Runs five concurrent validation gates inside every Ray worker. Each gate
   checks a different user through the profile-age, achievement, and Telegram
   filters.
6. Writes location-named CSVs under `new_output/` and an independent resume-state
   file per worker. Partial results stay in their location files if interrupted.
7. Reports the saved contact count. Runs do not merge into `contacts.csv`.

Gate threads never write CSV files directly. Their region coordinator assigns
each GitHub link once, serializes and atomically replaces the region CSV, and
only checkpoints a contiguous completed prefix. This prevents duplicate rows
and prevents a fast gate from advancing resume state past an unfinished user.

Each region is stored in numbered CSV shards containing at most 500 contacts:

```text
new_output/04_seattle_wa_1.csv
new_output/04_seattle_wa_2.csv
new_output/04_seattle_wa_3.csv
```

Only the current shard is rewritten. If it is open in Excel or otherwise
locked on Windows, the worker seals it early and continues in the next numbered
shard instead of failing. If the output directory itself is temporarily
unwritable, the worker retries with backoff until it succeeds or you press
`Ctrl+C`. Legacy unnumbered region files are split and moved into the
recoverable `legacy` subdirectory next to their output files.

Canada and the United Kingdom can be selected country-wide. Toronto, Vancouver,
Montreal, Ottawa, Calgary, London, Manchester, Edinburgh, Bristol, and Cambridge
are also available alongside the existing U.S. cities.

There is no application-level candidate limit. Each process continues until all
supported search partitions for its location have been enumerated and checked.
Configure the delay between profile checks in `.env` when needed:

```env
SCRAPE_DELAY_SECONDS=1.0
```

The delay is applied independently by each gate after its Telegram check, so
one region can have up to five validation requests in flight. With multiple
selected regions, total validation concurrency is `region count × 5`.

Progress is resumable, so another run continues each selected region from its
saved index.

## CSV browser

```bash
python gscraper.py ui run
```

The launcher accepts the same arguments: `gscraper ui run` when the project is
on your PATH, `.\gscraper.bat ui run` in Windows PowerShell, or
`./gscraper ui run` on Linux/macOS after `install.sh`. The UI opens your browser
at `http://127.0.0.1:8765` and runs until you press `Ctrl+C`; it does not start
a scrape or require tmux. It opens `new_output/` by default. No additional
runtime dependencies are needed.

- Select a CSV from the left sidebar, including files in subdirectories. Use
  the menu button or Settings to hide/show the sidebar.
- Existing CSVs gain an `is_read` column when opened. New contacts start with
  `is_read=false`. Opening a web, Telegram, or email link marks that row read;
  Ctrl/Cmd-click, middle-click, keyboard activation, and opening the link's
  context menu also count. Check or uncheck the box to set it manually.
- Read changes save immediately to the selected CSV as `true`/`false`. Read
  status is per file. Scraper rewrites and merges preserve the destination
  file's saved flags, including manually unchecked rows. New rows imported
  by a merge retain their source flag. Extra CSV columns are preserved.
- Every row is available in one scrolling table without pagination. Rows stay
  on one line; long values are clipped with an ellipsis. Hover to see the full
  value, drag a header edge to resize, or enter widths in Settings. Focus a
  header edge and use the arrow keys to resize with the keyboard.
- Clicking a cell copies its full value, even when clipped. Clicking a link
  also opens it in a new tab. Copying cell text marks its row as read and saves
  `is_read=true` to the CSV. This includes click copying, automatic drag copying,
  and ordinary Ctrl+C / Cmd+C or context-menu copying of selected table text.
  Selecting text without copying does not change its read status.
  Settings can disable click copying or enable
  automatic copying of text selected by dragging. Dragging text does not open
  its link. Ordinary text selection and Ctrl+C / Cmd+C remain available.
- Settings, column widths, the selected file, and sidebar visibility persist
  in this browser. Edit `githubscraper/web/state.js` to change defaults; use
  **Restore defaults** in Settings to discard saved preference overrides.
- Use **Refresh CSV** to reload scraper output, and the sidebar refresh button
  to discover new files. A changed/reordered row is rejected on save until you
  refresh, so a stale view cannot mark a different row. A locked CSV reports an
  error without replacing its contents.

Choose another directory or port, or suppress automatic browser opening:

```bash
python gscraper.py ui run --directory data/output --port 8766 --no-browser
```

The server listens only on this machine. CSVs must be UTF-8 (with or without a
BOM), comma-separated, with unique headers and consistent row lengths.

## Direct CLI

```bash
python github_scraper.py list
python github_scraper.py region 21
python github_scraper.py scrape "United Kingdom"
```

`--max-results N` remains available only when you intentionally want a short
manual test run. Omitting it performs the unlimited run.

Custom searches save to `new_output/<location>.csv` (for example,
`scrape "Boston, MA"` uses `new_output/boston_ma.csv`). Region runs keep their
numbered location files. Both commands still accept an explicit `--output` path.

## Data locations

- `new_output/*_1.csv`, `*_2.csv`, ...: location-specific region contacts,
  limited to 500 rows per file
- `new_output/<location>.csv`: custom location searches
- `data/output/`: historical exports; new runs do not update `contacts.csv`
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

Optional UI browser checks use temporary CSVs and block external navigation.
Install Playwright (`python -m pip install playwright`) and Chromium
(`python -m playwright install chromium`); Windows checks use installed Edge.
Then run `GSCRAPER_BROWSER_TESTS=1 python -m pytest -q` on Linux/macOS, or:

```powershell
$env:GSCRAPER_BROWSER_TESTS = "1"
python -m pytest -q
```
