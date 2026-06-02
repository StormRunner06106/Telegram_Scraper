# Changelog

## Latest Updates

### New Features

#### 1. Region-Based Scraping

- Added `regions.json` with 20 predefined US tech hub cities
- New command: `python github_scraper.py region <id>`
- Regions include: Austin, San Francisco, New York, Seattle, Boston, and 15 more

#### 2. Resume Capability

- Automatic progress tracking in `state.json`
- Resume from where you left off after interruption
- Progress saved every 10 users
- Handles Ctrl+C gracefully
- Use `--no-resume` flag to start fresh

#### 3. Company Filtering

- Detects 50+ major tech companies (Apple, Google, Microsoft, NVIDIA, Meta, etc.)
- New CSV column: `company` (populated if user works at a big company)
- Case-insensitive partial matching

#### 4. Name Matching Verification

- Extracts full name from Telegram profile page
- Compares with GitHub full name
- New CSV column: `nameMatch` with values:
  - `matched` - Names match exactly
  - `not matched` - Names don't match
  - `unknown` - One or both names missing

#### 5. Improved Location Search

- Changed from exact string matching to flexible component matching
- Example: `location:Austin location:Texas` instead of `location:"Austin, Texas, United States"`
- Finds 585x more users (78,435 vs 134 for Austin)
- Matches variations like "Austin, TX", "Austin, Texas", "ATX, Texas", etc.

#### 6. New Commands

- `list` - Show all regions and scraping progress
- `region <id>` - Scrape by region ID with resume support
- `scrape <location>` - Original location-based scraping

### Updated CSV Format

**Old format:**

```csv
link,email,telegramId,blog,years
```

**New format:**

```csv
link,email,telegramId,blog,years,company,nameMatch
```

### Files Added

- `regions.json` - Predefined regions
- `state.json` - Progress tracking (auto-generated, gitignored)
- `USAGE_EXAMPLES.md` - Detailed usage examples
- `CHANGELOG.md` - This file

### Breaking Changes

- None! Old usage still works: `python github_scraper.py scrape "Austin, Texas"`
- CSV format is backward compatible (new columns added at the end)

### Bug Fixes

- Fixed location search to find significantly more users
- Improved error handling for rate limits
- Better progress tracking and recovery

### Performance Improvements

- Progress saved incrementally (every 10 users)
- Duplicate detection using seen_links set
- Efficient state management with JSON files

## Migration Guide

### From Old Version

**Old usage:**

```bash
python github_scraper.py "Austin, Texas"
```

**New equivalent:**

```bash
python github_scraper.py scrape "Austin, Texas"
```

**Or use regions (recommended):**

```bash
python github_scraper.py region 1
```

### Updating Existing CSV Files

Old CSV files will continue to work. When you run the scraper again, it will:

1. Read existing contacts
2. Add new columns (`company`, `nameMatch`) to new entries
3. Preserve old entries as-is

To update old entries with new fields, delete the CSV and re-scrape.

## Future Enhancements

Potential improvements for future versions:

- Add more regions (international cities)
- Parallel scraping of multiple regions
- Export to JSON, SQLite, or other formats
- Web dashboard for monitoring progress
- Email notifications when scraping completes
- Advanced filtering (followers, repos, languages)
- Batch processing with queue system
