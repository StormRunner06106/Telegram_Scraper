# Quick Reference Card

## 🚀 Getting Started

```bash
# 1. Check environment
python check_env.py

# 2. Test setup
python test_setup.py

# 3. Run agent
python gscraper.py

# 4. Follow prompts
```

## 📋 Commands

### GScraper (Agent Mode)

```bash
python gscraper.py              # Interactive agent
```

### GitHub Scraper (CLI Mode)

```bash
python github_scraper.py list                    # List regions
python github_scraper.py region 1                # Scrape region 1
python github_scraper.py region 1 --no-resume    # Start fresh
python github_scraper.py scrape "Austin, Texas"  # Custom location
```

### Supabase Setup

```bash
python setup_supabase.py        # Interactive menu
# 1. Insert/Update regions
# 2. List regions
# 3. List states
# 4. Sync states from state.json to Supabase
# 5. Reset states
# 6. Show database status
# 7. Show SQL
```

### Environment Check

```bash
python check_env.py             # Check .env configuration
```

## 🔧 Environment Variables

```bash
# Required for higher limits
export GITHUB_TOKEN="your_token"

# Optional for Supabase sync
export SUPABASE_URL="https://xxx.supabase.co"
export SUPABASE_KEY="your_key"
```

## 📁 Important Files

| File                | Purpose                     |
| ------------------- | --------------------------- |
| `gscraper.py`       | Agent scraper (recommended) |
| `github_scraper.py` | CLI scraper                 |
| `setup_supabase.py` | Database setup              |
| `regions.json`      | 20 predefined regions       |
| `state.json`        | Progress tracking (auto)    |

## 🗄️ Supabase Tables

### Regions Table (Create This)

```sql
CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### States Table (Already Exists)

Your existing States table will be used as-is. No need to create it.

## 📊 Output Format

```csv
link,email,telegramId,blog,years,company,nameMatch
https://github.com/user,email@example.com,@user,blog.com,12,Google,matched
```

## 🎯 Filtering Criteria

- ✅ Account age > 8 years
- ✅ GitHub badges > 3
- ✅ Telegram account exists
- ✅ Company at major tech firm (optional)
- ✅ Name matching (GitHub ↔ Telegram)

## 🌍 Regions (20 US Tech Hubs)

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

## 🏢 Detected Companies (50+)

Apple, Google, Microsoft, Amazon, Meta, Netflix, NVIDIA, Tesla, SpaceX, Twitter, Uber, Airbnb, Stripe, Salesforce, Oracle, IBM, Intel, AMD, Qualcomm, Cisco, Adobe, PayPal, Square, Shopify, Spotify, Snap, Pinterest, Reddit, Dropbox, Slack, Zoom, Atlassian, GitHub, GitLab, Docker, and more...

## 🛑 Keyboard Shortcuts

- **Ctrl+C** - Pause and save progress
- **Y/n** - Confirm prompts (Y = yes, n = no)
- **Enter** - Accept default value

## 🔌 Network Resilience

GScraper automatically:

- Detects network disconnection
- Waits for reconnection (30s intervals)
- Resumes from last position
- No manual intervention needed

## 📈 Progress Tracking

### Check Local State

```bash
cat state.json
```

### Check Supabase State

```bash
python setup_supabase.py
# Select option 3: List states
```

### Watch Real-time

```bash
watch -n 5 cat state.json
```

## 🐛 Troubleshooting

| Issue            | Solution                                |
| ---------------- | --------------------------------------- |
| Rate limit       | Set `GITHUB_TOKEN`                      |
| Network error    | GScraper auto-retries                   |
| Supabase error   | Check `SUPABASE_URL` and `SUPABASE_KEY` |
| No results       | Verify region ID exists                 |
| Module not found | `pip install supabase`                  |

## 📖 Documentation

- `README_MAIN.md` - Main documentation
- `GSCRAPER_README.md` - Agent mode guide
- `SETUP_GUIDE.md` - Complete setup
- `USAGE_EXAMPLES.md` - CLI examples
- `PROJECT_SUMMARY.md` - Full overview

## ⚡ Quick Tips

1. Start with limit=20 for testing
2. Always use GitHub token
3. Enable Supabase for reliability
4. Use delay ≥1 second
5. Monitor progress regularly
6. Backup CSV files
7. Verify data quality

## 🎯 Common Workflows

### First Time Setup

```bash
pip install supabase
python setup_supabase.py  # Insert regions
export GITHUB_TOKEN="your_token"
export SUPABASE_URL="your_url"
export SUPABASE_KEY="your_key"
python test_setup.py
python gscraper.py
```

### Daily Scraping

```bash
python gscraper.py
# Select region → Input limit → Start
```

### Resume After Interruption

```bash
python gscraper.py
# Select same region → Auto-resumes
```

### Check Progress

```bash
python setup_supabase.py
# Option 3: List states
```

### Reset Progress

```bash
rm state.json
# Or use setup_supabase.py → Option 4
```

## 📞 Support

Run `python test_setup.py` to verify installation.

---

**Ready to scrape?** → `python gscraper.py` 🚀
