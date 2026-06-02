# Usage Examples

## Quick Start

### 1. List all available regions

```bash
python github_scraper.py list
```

Output:

```
Available regions:
ID    Name                           State
-------------------------------------------------------
1     Austin, TX                     Texas
2     San Francisco, CA              California
3     New York, NY                   New York
...

Region progress:
No progress saved yet.
```

### 2. Start scraping a region

```bash
python github_scraper.py region 1 --max-results 100 --delay 1
```

This will:

- Scrape Austin, TX (region ID 1)
- Process up to 100 users
- Wait 1 second between requests
- Save progress every 10 users to `state.json`
- Save qualified leads to `contacts.csv`

### 3. Resume after interruption

If you stop the scraper (Ctrl+C) or it hits rate limits, just run the same command again:

```bash
python github_scraper.py region 1 --max-results 100 --delay 1
```

It will automatically resume from where it left off.

### 4. Check progress

```bash
python github_scraper.py list
```

Output:

```
Region progress:
ID    Index      Processed    Status
----------------------------------------
1     45         45           in progress
```

### 5. Start fresh (ignore saved progress)

```bash
python github_scraper.py region 1 --no-resume
```

## Advanced Examples

### Scrape multiple regions sequentially

```bash
# Scrape Austin
python github_scraper.py region 1 --max-results 500

# Scrape San Francisco
python github_scraper.py region 2 --max-results 500

# Scrape New York
python github_scraper.py region 3 --max-results 500
```

### Use custom output file per region

```bash
python github_scraper.py region 1 --output austin_contacts.csv
python github_scraper.py region 2 --output sf_contacts.csv
```

### Scrape with GitHub token for higher limits

```bash
export GITHUB_TOKEN=your_token_here
python github_scraper.py region 1 --max-results 1000
```

Or:

```bash
python github_scraper.py region 1 --github-token your_token_here --max-results 1000
```

### Scrape by custom location (without regions)

```bash
python github_scraper.py scrape "Boulder, Colorado"
python github_scraper.py scrape "Toronto, Ontario, Canada"
```

## Understanding the Output

### CSV Format

```csv
link,email,telegramId,blog,years,company,nameMatch
https://github.com/user1,user@email.com,@user1,https://blog.com,12,Google,matched
https://github.com/user2,,@user2,,15,,not matched
https://github.com/user3,user3@email.com,@user3,,10,Microsoft,unknown
```

**Fields:**

- **link**: GitHub profile URL
- **email**: Public email from GitHub profile (if available)
- **telegramId**: Telegram username (format: @username)
- **blog**: Personal website/blog from GitHub profile
- **years**: Account age in years
- **company**: Company name if it's a major tech company, otherwise empty
- **nameMatch**:
  - `matched` - GitHub and Telegram names match
  - `not matched` - Names don't match
  - `unknown` - One or both names are missing

### State File Format

```json
[
  {
    "region_id": 1,
    "index": 1238,
    "is_end": false,
    "total_processed": 1238
  }
]
```

**Fields:**

- **region_id**: Region being scraped
- **index**: Current position in the GitHub user list
- **is_end**: `true` if scraping completed, `false` if in progress
- **total_processed**: Total number of users processed (including skipped ones)

## Tips

1. **Start small**: Test with `--max-results 20` first to verify everything works
2. **Use delays**: Keep `--delay 1` or higher to avoid aggressive scraping
3. **Monitor rate limits**: If you hit GitHub rate limits, the scraper will stop and save progress
4. **Resume anytime**: You can stop (Ctrl+C) and resume without losing progress
5. **Check progress**: Run `python github_scraper.py list` to see current progress
6. **Big companies**: The scraper automatically detects 50+ major tech companies
7. **Name verification**: Use the `nameMatch` field to verify identity consistency

## Troubleshooting

### "Region already completed"

```bash
# Start fresh
python github_scraper.py region 1 --no-resume
```

### Rate limit errors

```bash
# Use a GitHub token
export GITHUB_TOKEN=your_token_here
python github_scraper.py region 1
```

### Want to reset all progress

```bash
# Delete state file
rm state.json

# Or edit it manually to remove specific regions
```
