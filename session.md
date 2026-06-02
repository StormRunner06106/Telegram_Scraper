---
agent_doc_session: f5857bac-7d40-46ab-8377-dc58f1c65264
agent: codex
---

# Session: Telegram Scraper

## User

Add this command, gscraper status, then show fetched lead amount according to locations. and if I add argument to command like gscraper status --new, then show never fetched locations. so if this command run - gscraper --new, then show never tried location list at location selection step.


<!-- agent:exchange -->
### Re: gscraper status — gpt-5

Implemented the requested status/new-location behavior.

Changed:
- Added `gscraper status` to show location progress with fetched count and status.
- Added `gscraper status --new` to show only locations with no saved state, meaning never tried.
- Added `gscraper --new` for the interactive agent so the region selection step lists only never-tried locations.
- Added regression coverage for the never-tried filtering/status output.

Verified with:
- `python -m unittest tests.test_status`
- `python -m compileall githubscraper gscraper.py github_scraper.py tests/test_status.py`
- `python gscraper.py status`
- `python gscraper.py status --new`
- `printf 'q\\n' | python gscraper.py --new`

One implementation detail: “never tried” is based on no saved state row for the region. If a region has a saved state row with `total_processed = 0`, it is treated as tried/in progress rather than new.
<!-- agent:boundary:725ca811 -->
<!-- /agent:exchange -->
