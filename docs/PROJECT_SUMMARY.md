# GitHub Scraper Project - Complete Summary

## Overview

A comprehensive GitHub user scraper that finds developers by location, validates their Telegram accounts, checks company affiliations, and verifies identity consistency across platforms.

## Project Structure

```
GithubScraper/
├── Core Scraper
│   ├── github_scraper.py      # Main scraper with CLI
│   ├── gscraper.py            # Agent-based interactive scraper
│   └── setup_supabase.py      # Database setup utility
│
├── Configuration
│   ├── regions.json           # 20 predefined US tech hubs
│   ├── state.json             # Progress tracking (auto-generated)
│   ├── .env.example           # Environment template
│   └── requirements.txt       # Python dependencies
│
├── Documentation
│   ├── README.md              # Main documentation
│   ├── GSCRAPER_README.md     # Agent scraper guide
│   ├── SETUP_GUIDE.md         # Complete setup instructions
│   ├── USAGE_EXAMPLES.md      # Usage examples
│   ├── CHANGELOG.md           # Version history
│   └── PROJECT_SUMMARY.md     # This file
│
├── Launchers
│   ├── gscraper.bat           # Windows launcher
│   └── gscraper.sh            # Linux/Mac launcher
│
└── Tests
    ├── test_features.py       # Feature tests
    ├── test_regions.py        # Region/state tests
    └── test_search.py         # Search tests
```

## Two Scraping Modes

### 1. github_scraper.py (CLI Mode)

**Best for**: Quick scrapes, scripting, automation

**Features**:

- Command-line interface
- Three commands: `list`, `scrape`, `region`
- Manual resume with `--no-resume` flag
- Direct control over all parameters

**Usage**:

```bash
# List regions
python github_scraper.py list

# Scrape by region
python github_scraper.py region 1 --max-results 100

# Scrape by location
python github_scraper.py scrape "Austin, Texas"
```

### 2. gscraper.py (Agent Mode)

**Best for**: Long-running, unattended scraping

**Features**:

- Interactive step-by-step CLI
- Network resilience (auto-retry)
- Supabase real-time sync
- Graceful Ctrl+C handling
- Smart file naming with index ranges
- Automatic resume

**Usage**:

```bash
python gscraper.py
# Follow interactive prompts
```

## Key Features

### 1. Filtering Criteria

- ✅ Account age > 8 years
- ✅ GitHub badges > 3
- ✅ Telegram account exists
- ✅ Company at major tech firm (50+ companies)
- ✅ Name matching between GitHub and Telegram

### 2. Data Collection

- GitHub profile (username, email, blog, company, name)
- Telegram profile (username, full name)
- Account age in years
- Company affiliation
- Name match status

### 3. Output Format (CSV)

```csv
link,email,telegramId,blog,years,company,nameMatch
https://github.com/user,email@example.com,@user,blog.com,12,Google,matched
```

### 4. Progress Tracking

```json
{
  "region_id": 1,
  "index": 1238,
  "is_end": false,
  "total_processed": 1238
}
```

### 5. Network Resilience

- Detects network disconnection
- Waits for reconnection (30s intervals)
- Auto-resumes from last position
- No data loss

### 6. Supabase Integration

- Real-time state synchronization
- Cross-machine progress tracking
- Centralized region management
- State history

## Regions

20 predefined US tech hubs:

| ID  | City           | State                |
| --- | -------------- | -------------------- |
| 1   | Austin         | Texas                |
| 2   | San Francisco  | California           |
| 3   | New York       | New York             |
| 4   | Seattle        | Washington           |
| 5   | Boston         | Massachusetts        |
| 6   | Los Angeles    | California           |
| 7   | Chicago        | Illinois             |
| 8   | Denver         | Colorado             |
| 9   | Portland       | Oregon               |
| 10  | Miami          | Florida              |
| 11  | Atlanta        | Georgia              |
| 12  | Dallas         | Texas                |
| 13  | San Diego      | California           |
| 14  | Phoenix        | Arizona              |
| 15  | Philadelphia   | Pennsylvania         |
| 16  | Washington     | District of Columbia |
| 17  | Raleigh        | North Carolina       |
| 18  | Salt Lake City | Utah                 |
| 19  | Minneapolis    | Minnesota            |
| 20  | Nashville      | Tennessee            |

## Big Companies List (50+)

Apple, Google, Microsoft, Amazon, Meta, Facebook, Netflix, NVIDIA, Tesla, SpaceX, Twitter, Uber, Lyft, Airbnb, Stripe, Salesforce, Oracle, IBM, Intel, AMD, Qualcomm, Cisco, Adobe, PayPal, Square, Shopify, Spotify, Snap, Pinterest, Reddit, Dropbox, Slack, Zoom, Atlassian, GitHub, GitLab, Docker, VMware, Dell, HP, Samsung, Sony, Tencent, Alibaba, Baidu, ByteDance, TikTok, Huawei, Xiaomi, Lenovo, ASUS, Acer

## Setup Requirements

### Minimum (No Supabase)

- Python 3.10+
- Internet connection

### Recommended (With Supabase)

- Python 3.10+
- `supabase` package
- Supabase account
- GitHub token

### Environment Variables

```bash
GITHUB_TOKEN=your_token          # Recommended
SUPABASE_URL=your_url            # Optional
SUPABASE_KEY=your_key            # Optional
```

## Quick Start

### 1. Basic Setup

```bash
# Clone/download project
cd GithubScraper

# Install dependencies (optional)
pip install supabase
```

### 2. Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 3. Run

```bash
# Interactive agent mode
python gscraper.py

# Or CLI mode
python github_scraper.py list
python github_scraper.py region 1
```

## Performance

### Search Improvements

- **Old**: Exact string matching → 134 users in Austin
- **New**: Flexible component matching → 78,435 users in Austin
- **Improvement**: 585x more results

### Rate Limits

- **Without token**: ~60 requests/hour
- **With token**: 5,000 requests/hour
- **Recommendation**: Always use token for serious scraping

### Typical Speed

- ~1 second per user (with delay)
- ~3,600 users per hour
- ~86,400 users per day (24/7)

## Use Cases

### 1. Lead Generation

Find developers at major tech companies with verified Telegram accounts.

### 2. Recruitment

Identify experienced developers (8+ years) with active GitHub profiles.

### 3. Market Research

Analyze developer distribution across US tech hubs.

### 4. Community Building

Find developers for Telegram communities or groups.

### 5. Data Analysis

Study correlations between location, company, and GitHub activity.

## Best Practices

1. **Start small**: Test with 20 users first
2. **Use delays**: Keep delay ≥ 1 second
3. **Enable Supabase**: Track progress reliably
4. **Use GitHub token**: Avoid rate limits
5. **Monitor progress**: Check state regularly
6. **Backup data**: Keep CSV files safe
7. **Respect limits**: Don't abuse APIs
8. **Verify data**: Spot-check results

## Troubleshooting

### Common Issues

| Issue          | Solution              |
| -------------- | --------------------- |
| Rate limit     | Use GitHub token      |
| Network error  | GScraper auto-retries |
| Supabase error | Check credentials     |
| No results     | Check region ID       |
| Duplicate data | CSV upsert handles it |

### Debug Mode

Add print statements in `github_scraper.py`:

```python
print(f"Debug: Processing user {username}")
```

### Logs

Check console output for:

- Skipped users (with reasons)
- API errors
- Progress updates
- Network status

## Future Enhancements

### Planned

- [ ] International regions
- [ ] More social platforms (LinkedIn, Twitter)
- [ ] Advanced filtering (languages, repos)
- [ ] Web dashboard
- [ ] Email notifications
- [ ] Parallel scraping
- [ ] Export to JSON/SQLite

### Community Contributions

- Add more regions to `regions.json`
- Add more companies to `NORMAL_BIG_COMPANIES`
- Improve name matching algorithm
- Add more social platforms

## License

MIT License (or specify your license)

## Credits

Built for efficient, ethical developer lead generation with respect for API rate limits and user privacy.

## Support

- Read documentation in `docs/` folder
- Check examples in `USAGE_EXAMPLES.md`
- Review setup in `SETUP_GUIDE.md`
- See changes in `CHANGELOG.md`

## Version

Current: 2.0.0 (Agent Mode Release)

## Last Updated

2026-05-07
